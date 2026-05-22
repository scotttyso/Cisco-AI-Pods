"""BMC API wrapper for Intersight UCS provisioning."""
# pylint: disable=invalid-name,missing-class-docstring,missing-function-docstring,too-many-arguments,too-many-positional-arguments,too-many-return-statements,too-many-branches,too-many-statements,too-many-locals
# =============================================================================
# Source Modules
# =============================================================================
import sys
from pathlib import Path


def prRed(skk):
    print(f"\033[91m {skk}\033[00m")


SCRIPT_PATH = Path(__file__).resolve().parent
CLASSES_PATH = SCRIPT_PATH / 'src'
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_PATH) not in sys.path:
    sys.path.insert(1, str(SCRIPT_PATH))
if str(CLASSES_PATH) not in sys.path:
    sys.path.insert(2, str(CLASSES_PATH))

try:
    from src.intersight import api as intersight_api
    from roles.intersight_ucs_provision.library.src import notifications, pcolor
    from copy import deepcopy
    from dotmap import DotMap
    import inspect
    import jinja2
    import json
    import os
    import re
    import requests
    import time
    import urllib3
except ImportError as e:
    prRed(f'src/bmc.py - !!! ERROR !!!\n{e.__class__.__name__}')
    prRed(f" Module {e.name} is required to run this script")
    prRed(f" Install the module using the following: `pip install {e.name}`")
    sys.exit(1)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global options for debugging
print_payload = False
print_response_always = True
print_response_on_fail = True

# Log levels 0 = None, 1 = Class only, 2 = Line
log_level = 2

# =============================================================================
# Configure C885A BMC Settings
# =============================================================================


class api:
    def __init__(self, category=None, type=None):  # pylint: disable=redefined-builtin
        self.category = category
        self.type = type

    # =========================================================================
    # Function - API Authentication
    # =========================================================================
    @staticmethod
    def auth(kwargs):
        url = f"https://{kwargs.hostname}"
        s = requests.Session()
        s.auth = (kwargs.username, kwargs.password)
        auth = ''
        while auth == '':
            try:
                auth = s.post(url, verify=False)
            except requests.exceptions.ConnectionError as e:
                pcolor.Red(
                    f"Connection error, pausing before retrying. Error: {e}")
                time.sleep(5)
            except Exception as e:
                pcolor.Red(f'{url}')
                pcolor.Red(
                    f"!!! ERROR !!! Method {(inspect.currentframe().f_code.co_name).upper()} Failed. Exception: {e}\n")
                raise
        return s, url

    # =========================================================================
    # Function - API Request Wrapper
    # =========================================================================
    @staticmethod
    def _request(  # pylint: disable=inconsistent-return-statements
            method,
            kwargs,
            ok_statuses,
            payload_mode=None,
            allow_empty=False):
        s, url = api.auth(kwargs)
        r = ''
        while r == '':
            try:
                full_url = f'{url}{kwargs.uri}'
                pcolor.Cyan(f"     * {method}: {full_url}")
                req_kwargs = {'verify': False}
                if payload_mode == 'json':
                    req_kwargs['json'] = kwargs.payload
                elif payload_mode == 'data':
                    req_kwargs['data'] = kwargs.payload
                r = getattr(s, method)(full_url, **req_kwargs)

                if print_response_always:
                    pcolor.Purple(
                        f"     * {method}: {r.status_code} success with {kwargs.uri}")

                if r.status_code not in ok_statuses:
                    notifications.error_requests(
                        method, r.status_code, r.text, kwargs.uri)

                if r.status_code == 204:
                    return {}
                if allow_empty and len(r.text) == 0:
                    return {}
                return r.json()
            except requests.exceptions.ConnectionError as e:
                pcolor.Red(
                    f"Connection error, pausing before retrying. Error: {e}")
                time.sleep(5)
            except Exception as e:
                pcolor.Red(f'{url}/{kwargs.uri}')
                pcolor.Red(
                    f"!!! ERROR !!! Method {method.upper()} Failed. Exception: {e}\n")
                raise

    # =========================================================================
    # Function - API - GET
    # =========================================================================
    @staticmethod
    def get(kwargs):
        return api._request('get', kwargs, ok_statuses={200, 404})

    # =========================================================================
    # Function - API - PATCH
    # =========================================================================
    @staticmethod
    def patch(kwargs):
        return api._request(
            'patch',
            kwargs,
            ok_statuses={
                200,
                201,
                202,
                203,
                204},
            payload_mode='json',
            allow_empty=True)

    # =========================================================================
    # Function - API - POST
    # =========================================================================
    @staticmethod
    def post(kwargs):
        return api._request(
            'post',
            kwargs,
            ok_statuses={
                200,
                201,
                202,
                203,
                204},
            payload_mode='data')

    # =========================================================================
    # Function - API - PUT
    # =========================================================================
    @staticmethod
    def put(kwargs):
        return api._request(
            'put',
            kwargs,
            ok_statuses={
                200,
                201,
                202,
                203,
                204},
            payload_mode='json')

# =============================================================================
# Configure C885A BMC Settings
# =============================================================================


class build:
    def __init__(self, category=None, type=None):  # pylint: disable=redefined-builtin
        self.category = category
        self.type = type

    # =========================================================================
    # Function - Shared: GET → compare → PATCH helper
    # =========================================================================
    def get_compare_patch(
            self,
            uri,
            item,
            kwargs,
            method='patch',
            type_override=None):
        kwargs.uri = uri
        result = api.get(kwargs)
        api_body = self.create_api_body(item, kwargs)
        changed = self.compare_body_result(api_body, result)
        if changed:
            kwargs.payload = api_body
            patch_type = type_override or self.type
            if method == 'patch':
                api(category=self.category, type=patch_type).patch(kwargs)
            elif method == 'put':
                api(category=self.category, type=patch_type).put(kwargs)
        return changed, kwargs

    # =========================================================================
    # UCS - System - BIOS
    # =========================================================================
    def bios(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        ikeys = item.keys()
        if 'bios_template' in ikeys:
            template_name = item.bios_template
            templates = kwargs.ezdata[f'intersight.{self.category}.{self.type}'].allOf[1].properties.bios_template.enum
            btemplates = kwargs.ezdata[f'intersight.{self.category}.{self.type}.templates'].properties
            if template_name not in templates:
                pcolor.Red(
                    f'!!! ERROR !!! Bios Template "{template_name}" was not found in "intersight.{self.category}.{self.type}.templates".')
                pcolor.Red(
                    f'Available templates are: {", ".join(sorted(list(templates.keys())))}')
                raise ValueError(
                    f'BIOS template "{template_name}" was not found in "intersight.{self.category}.{self.type}.templates"')
            btemplate = btemplates[re.sub(
                r'-tpm$', '', item.bios_template, flags=re.IGNORECASE)]
            if '-tpm' in (item.bios_template).lower():
                item = btemplate | btemplates.tpm | item
            else:
                item = btemplate | item
        kwargs.uri = '/redfish/v1/Systems/system/Bios'
        result = api.get(kwargs)
        api_body = self.create_api_body(item, kwargs)
        changed = self.compare_body_result(api_body, result)
        if changed:
            kwargs.uri = '/redfish/v1/Systems/system/Bios/Settings'
            kwargs.payload = api_body
            api.patch(kwargs)
            kwargs.reboot_required = True
        notifications.section_end(self.category, self.type)
        # =====================================================================
        # return kwargs
        # =====================================================================
        return kwargs

    # =========================================================================
    # Function - Create API Request Body
    # =========================================================================
    def create_api_body(self, item, kwargs):
        if re.search(r'bios|certificate_management', self.type):
            item = getattr(self, self.type)(item, kwargs)

        template_dir = os.path.join(
            os.path.dirname(
                kwargs.script_path),
            'templates',
            'c88xA',
            f'{self.category}')
        template_name = f'{self.type}.json.j2'
        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=False)

        render_item = item.toDict() if hasattr(item, 'toDict') else item
        rendered = template_env.get_template(template_name).render(
            item=render_item,
            sensitive_vars=kwargs.sensitive_vars
        )
        try:
            api_body = json.loads(rendered)
        except json.JSONDecodeError as exc:
            policy_title = notifications.mod_pol_description(
                (self.type.replace('_', ' ')).capitalize())
            pcolor.Red(
                f'!!! ERROR !!! Failed to parse rendered JSON for {policy_title} template '
                f'`{template_name}` (line {exc.lineno}, column {exc.colno}).')
            start = max(1, exc.lineno - 2)
            end = min(len(rendered.splitlines()), exc.lineno + 2)
            for line_no in range(start, end + 1):
                marker = '>>' if line_no == exc.lineno else '  '
                pcolor.Yellow(
                    f'{marker} {line_no:4}: {rendered.splitlines()[line_no - 1]}')
            raise
        if not isinstance(api_body, dict):
            policy_title = notifications.mod_pol_description(
                (self.type.replace('_', ' ')).capitalize())
            pcolor.Red(
                f'!!! ERROR !!! {policy_title} template did not render to a dictionary payload.')
            raise ValueError(
                f'{policy_title} template did not render to a dictionary payload')
        return api_body

    # =========================================================================
    # Function - Compare Body Result for Differences
    # =========================================================================
    def compare_body_result(self, api_body, result):
        expected = deepcopy(api_body)
        current = deepcopy(result)
        differences = []

        def list_sort_key(value):
            try:
                return (1, 0, json.dumps(value, sort_keys=True))
            except TypeError:
                return (1, 1, str(value))

        def normalize_for_compare(value, path=''):
            if isinstance(value, dict):
                return {
                    k: normalize_for_compare(v, f'{path}.{k}' if path else k)
                    for k, v in value.items()
                }
            if isinstance(value, list):
                normalized_list = [
                    normalize_for_compare(v, f'{path}[{idx}]' if path else f'[{idx}]')
                    for idx, v in enumerate(value)
                ]
                if self.type == 'boot_order' and path == 'BootDevices':
                    return normalized_list
                return sorted(normalized_list, key=list_sort_key)
            return value

        expected = normalize_for_compare(expected)
        current = normalize_for_compare(current)

        def is_sensitive_path(path, key_name=''):
            check = f'{path}.{key_name}'.lower(
            ) if key_name else str(path).lower()
            sensitive_terms = (
                'password',
                'passphrase',
                'private_key',
                'privatekey',
                'existingkey',
                'newkey',
                'secret',
                'token',
            )
            return any(term in check for term in sensitive_terms)

        def sanitize_for_display(value, path='', key_name=''):
            if is_sensitive_path(path, key_name):
                return '__SENSITIVE__'
            return value

        def format_value(value):
            if value == '__SENSITIVE__':
                return 'sensitive'
            try:
                text = json.dumps(value, sort_keys=True)
            except TypeError:
                text = str(value)
            if len(text) > 180:
                return f"{text[:177]}..."
            return text

        def record_diff(
                path,
                expected_value,
                current_value,
                reason='value mismatch',
                key_name=''):
            expected_display = sanitize_for_display(
                expected_value, path, key_name)
            current_display = sanitize_for_display(
                current_value, path, key_name)
            differences.append(
                f"{path or '<root>'}: {reason} | expected={format_value(expected_display)} | current={format_value(current_display)}"
            )

        def values_differ(v1, v2, path='', key_name=''):
            # Sensitive/write-only fields (passwords, tokens, keys, etc.) are
            # not reliably returned by GET, so exclude them from equality
            # checks.
            if is_sensitive_path(path, key_name):
                return False
            changed = False
            if isinstance(v1, dict):
                if not isinstance(v2, dict):
                    record_diff(path, v1, v2, 'type mismatch', key_name)
                    return True
                for k, v in v1.items():
                    k_path = f'{path}.{k}' if path else k
                    if is_sensitive_path(k_path, k):
                        continue
                    if k not in v2:
                        record_diff(k_path, v, None, 'missing key', k)
                        changed = True
                        continue
                    if values_differ(v, v2[k], k_path, k):
                        changed = True

                return changed

            if isinstance(v1, list):
                if not isinstance(v2, list):
                    record_diff(path, v1, v2, 'type mismatch', key_name)
                    return True
                if len(v2) < len(v1):
                    record_diff(
                        path, v1, v2, 'list length/type mismatch', key_name)
                    changed = True
                for idx, item in enumerate(v1):
                    if idx >= len(v2):
                        break
                    idx_path = f'{path}[{idx}]' if path else f'[{idx}]'
                    if values_differ(item, v2[idx], idx_path, key_name):
                        changed = True
                return changed

            if v1 != v2:
                record_diff(path, v1, v2, 'value mismatch', key_name)
                return True
            return False

        changed = values_differ(expected, current)
        if changed and len(differences) > 0:
            pcolor.Yellow(
                f'     - Differences found for `{self.category}` -> {self.type} ({len(differences)}):')
            max_show = 1024
            for diff in differences[:max_show]:
                pcolor.Yellow(f'       * {diff}')
            if len(differences) > max_show:
                pcolor.Yellow(
                    f'       * ... {len(differences) - max_show} additional differences omitted')
        return changed

    # =========================================================================
    # Function - UCS C880/C885 BMC - Nodes
    # =========================================================================
    def configure_server(self, kwargs):
        def run_policy_setup(item, policy, kwargs):
            if hasattr(
                    item,
                    f'{policy}_policy') and getattr(
                    item,
                    f'{policy}_policy') is not None:
                indx = next((i for i, p in enumerate(
                    kwargs.imm_dict.orgs[kwargs.org].policies[policy]) if p['name'] == getattr(item, f'{policy}_policy')), None)
                if indx is not None:
                    pitem = kwargs.imm_dict.orgs[kwargs.org].policies[policy][indx]
                    getattr(
                        build(
                            category=self.type,
                            type=policy),
                        f'{policy}')(
                        pitem,
                        kwargs)
            return kwargs
        policy_list = ['ipmi_over_lan', 'local_user', 'ldap', 'power', 'bios']
        reconcile_resources = list(
            {t.name: p | t for p in kwargs.resources for t in p.targets}.values())
        for v in reconcile_resources:
            v.pop('targets', None)
        for item in reconcile_resources:
            kwargs.server_item = item
            password = kwargs.sensitive_vars.get(
                f'local_user_password_{item.password}', '')
            kwargs = kwargs | DotMap(
                username=item.username,
                password=password,
                reboot_required=False)
            kwargs = build(
                category=self.type,
                type='device_connector').device_connector(
                item,
                kwargs)
            for e in policy_list:
                kwargs = run_policy_setup(item, e, kwargs)
            # =================================================================
            # Reboot Server if required
            # =================================================================
            if kwargs.reboot_required is True:
                pcolor.Cyan(
                    f"     * {item.server_address} requires a reboot to apply changes.")
                self.reboot_system(item, kwargs)
            # =================================================================
            # return kwargs
            # =================================================================
        return kwargs

    # =========================================================================
    # Function - UCS - BMC Managers - DNS
    # =========================================================================
    def dns(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        self.get_compare_patch(
            '/redfish/v1/Managers/bmc/EthernetInterfaces/eth0', item, kwargs)
        pcolor.Cyan(
            "     * Pausing to allow time for DNS settings to take effect before claiming in Intersight.")
        time.sleep(10)
        notifications.section_end(self.category, self.type)

    # =========================================================================
    # Function - UCS - Device Connector - Registration
    # =========================================================================
    def device_connector(self, item, kwargs):
        # =====================================================================
        # Load Variables and Send Begin Notification
        # =====================================================================
        notifications.section_begin(self.category, self.type)
        kwargs.uri = '/connector/Systems'
        sys_data = api.get(kwargs)
        if sys_data[0]['AccountOwnershipState'] != 'Claimed':
            # =================================================================
            # Configure Shared Services (DNS, NTP, Proxy) if specified in YAML before claiming in Intersight
            # =================================================================
            ntp = DotMap()
            if item.get('ntp_policy', None):
                indx = next((i for i, p in enumerate(
                    kwargs.imm_dict.orgs[kwargs.org].policies.ntp) if p['name'] == item.ntp_policy), None)
                if indx is not None:
                    ntp = kwargs.imm_dict.orgs[kwargs.org].policies.ntp[indx]
            pdata = DotMap(
                domain_name=('.').join(item.name.split('.')[1:]),
                hostname=item.name,
                dns_servers=kwargs.shared_services.get('dns_servers'),
                ntp_servers=ntp.get('ntp_servers', []),
            )
            if kwargs.shared_services.get('dns_servers') and len(
                    kwargs.shared_services.dns_servers) > 0:
                build(category=self.category, type='dns').dns(pdata, kwargs)
            if isinstance(
                    ntp, DotMap) and ntp.get(
                    'ntp_servers', None) and len(
                    ntp.ntp_servers) > 0:
                build(category=self.category, type='ntp').ntp(ntp, kwargs)
            if kwargs.shared_services.get('proxy_servers') and len(
                    kwargs.shared_services.proxy_servers) > 0:
                pdata = kwargs.shared_services.get('proxy_servers')
                build(
                    category=self.category,
                    type='proxy_settings').proxy_settings(
                    pdata,
                    kwargs)
            kwargs.uri = '/connector/DeviceIdentifiers'
            # =================================================================
            # Claim in Intersight if not already Claimed
            # =================================================================
            device_ids = api.get(kwargs)
            valid_time = 0
            max_attempts = 10
            attempt = 0
            while valid_time < 60:
                if attempt >= max_attempts:
                    raise TimeoutError(
                        f"Security token for {item.server_address} never reached 60 s after {max_attempts} attempts.")
                kwargs.uri = '/connector/SecurityTokens'
                token = api.get(kwargs)
                valid_time = token[0]['Duration']
                if valid_time < 60:
                    pcolor.Cyan(
                        "     * Waiting for Security Token to be valid for at least 60 seconds.")
                    pcolor.Cyan(
                        f"     * Current Security Token Duration: {valid_time} seconds")
                    time.sleep(60)
                attempt += 1
            pcolor.Cyan(
                f"     * {item.server_address} is not Claimed, claiming in Intersight Now.")
            kwargs = kwargs | DotMap(
                api_body={
                    'SecurityToken': token[0]['Token'],
                    'SerialNumber': device_ids[0]['Id']},
                method='post',
                uri='asset/DeviceClaims')
            kwargs = intersight_api(
                category='system',
                type='device_claim').calls(kwargs)
        else:
            pcolor.Cyan(
                f"     * {item.server_address} is already claimed in Intersight.")
        # =====================================================================
        # return kwargs
        # =====================================================================
        return kwargs

    # =========================================================================
    # Function - UCS - BMC Managers - Accounts - IPMI over LAN
    # =========================================================================
    def ipmi_over_lan(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        self.get_compare_patch(
            '/redfish/v1/Managers/bmc/NetworkProtocol', item, kwargs)
        notifications.section_end(self.category, self.type)
        return kwargs

    # =========================================================================
    # Function - UCS - BMC Managers - Accounts - LDAP
    # =========================================================================
    def ldap(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        self.get_compare_patch('/redfish/v1/AccountService', item, kwargs)
        notifications.section_end(self.category, self.type)
        return kwargs

    # =========================================================================
    # Function - UCS - BMC Managers - Accounts - Local User
    # =========================================================================
    def local_user(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        kwargs.uri = '/redfish/v1/AccountService/Accounts'
        for e in item.users:  # Always PATCH — accounts include write-only password fields, compare is skipped intentionally
            if not e.username == kwargs.server_item.username:
                api_body = self.create_api_body(e, kwargs)
                kwargs.payload = api_body
                api.patch(kwargs)
        notifications.section_end(self.category, self.type)
        return kwargs

    # =========================================================================
    # Function - UCS - BMC Managers - Network Protocols - NTP
    # =========================================================================
    def ntp(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        for k, v in {'ntp': '/redfish/v1/Managers/bmc/NetworkProtocol',
                     'timezone': '/redfish/v1/Managers/bmc'}.items():
            self.get_compare_patch(v, item, kwargs, type_override=k)
        pcolor.Cyan(
            "     * Pausing to allow time for NTP settings to take effect before claiming in Intersight.")
        time.sleep(10)
        notifications.section_end(self.category, self.type)

    # =========================================================================
    # Function - UCS - Device Connector -> Proxy Settings
    # =========================================================================
    def proxy_settings(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        self.get_compare_patch(
            'connector/HttpProxies',
            item,
            kwargs,
            method='put')
        pcolor.Cyan(
            "     * Pausing to allow time for Proxy settings to take effect before claiming in Intersight.")
        time.sleep(20)
        notifications.section_end(self.category, self.type)

    # =========================================================================
    # Function - Reboot the System
    # =========================================================================
    def reboot_system(self, item, kwargs):
        kwargs = kwargs | DotMap(
            method='post',
            payload={"ResetType": "GracefulRestart"},
            uri='/redfish/v1/Systems/system/Actions/ComputerSystem.Reset'
        )
        rdata = api.post(kwargs)
        if print_response_always:
            pcolor.Purple(f"     * post: {rdata} success with {kwargs.uri}")
        if print_response_on_fail and rdata.get('error', None):
            err_msg = rdata.get('error', {}).get('message', 'Unknown Error')
            pcolor.Red(f"!!! ERROR !!! POST Failed. Exception: {err_msg}")
            raise RuntimeError(
                f"Reboot POST failed for {item.server_address}: {err_msg}")
        pcolor.Cyan(
            f"     * Rebooting {item.server_address} to apply Changes.")

    # =========================================================================
    # Function - UCS - System - Power Restore
    # =========================================================================
    def power(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        _, kwargs = self.get_compare_patch(
            '/redfish/v1/Systems/system', item, kwargs)
        notifications.section_end(self.category, self.type)
        return kwargs

    # =========================================================================
    # Function - UCS - BMC Managers - Accounts - SSH
    # =========================================================================
    def ssh(self, item, kwargs):
        notifications.section_begin(self.category, self.type)
        self.get_compare_patch(
            '/redfish/v1/Managers/bmc/NetworkProtocol', item, kwargs)
        notifications.section_end(self.category, self.type)
        return kwargs
