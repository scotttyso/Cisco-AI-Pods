"""Intersight system_software_repository class."""
# Copyright (c) 2026 Cisco Systems, Inc. and its affiliates.
# All rights reserved.
# =============================================================================
# Source Modules
# =============================================================================
import sys
from .. import notifications, pcolor
def prRed(skk): print("\033[91m {}\033[00m" .format(skk))


try:
    from .. import shared_functions
    from copy import deepcopy
    from dotmap import DotMap
    from operator import itemgetter
    import json
    import numpy
    import os
    import re
    import time
except ImportError as e:
    prRed(
        f'src/intersight/system_software_repository.py - !!! ERROR !!!\n{e.__class__.__name__}')
    prRed(f" Module {e.name} is required to run this script")
    prRed(f" Install the module using the following: `pip install {e.name}`")
    sys.exit(1)

# Lazy imports to resolve cross-module class references


def api(*args, **kwargs):
    from .api import api as _api
    return _api(*args, **kwargs)


# =============================================================================
# Intersight -> System -> Software Repository Class
# =============================================================================
class system_software_repository(object):
    def __init__(self, category=None, type=None):
        self.category = category
        self.type = type

    # =========================================================================
    # Function - OS Configuration Files
    # =========================================================================
    def os_configuration_files(self, kwargs):
        org_moid = kwargs.org_moids[kwargs.org].moid
        kwargs = kwargs | DotMap(
            api_filter=f"Name in ('{org_moid}','shared')",
            method='get',
            uri='os/Catalogs')
        kwargs = api('os_catalog').calls(kwargs)
        catalog_moids = kwargs.pmoids
        kwargs.api_filter = f"Catalog.Moid in ('{catalog_moids[org_moid].moid}','{catalog_moids.shared.moid}')"
        kwargs = kwargs | DotMap(uri='os/ConfigurationFiles')
        kwargs = api('os_configuration').calls(kwargs)
        kwargs.org_catalog_moid = catalog_moids[org_moid].moid
        kwargs.os_cfg_moids = kwargs.pmoids
        kwargs.os_cfg_results = kwargs.results
        return kwargs

    # =========================================================================
    # Function - Build Azure Stack HCI Operating System Auto Install File
    # =========================================================================
    def os_configuration_files_azure_stack(self, kwargs):
        # =====================================================================
        # Load Windows Languages and Timezone
        # =====================================================================
        # windows_language = DotMap(language_pack  = kwargs.imm_dict.wizard.windows_install.language_pack,
        # layered_driver =
        # kwargs.imm_dict.wizard.windows_install.layered_driver)
        windows_language = DotMap(
            language_pack='English - United States',
            layered_driver=0)
        kwargs = shared_functions.windows_languages(windows_language, kwargs)
        kwargs = shared_functions.windows_timezones(kwargs)
        # =====================================================================
        # Upload the Operating System Configuration File
        # =====================================================================
        answer = os.path.join(
            kwargs.script_path,
            'examples',
            'azure_stack_hci',
            '23H2',
            'AzureStackHCIIntersight.xml')
        vsplist = (kwargs.os_version.name.split(' '))
        version = f'{vsplist[0]}{vsplist[2]}'
        ctemplate = answer.split(os.sep)[-1]
        template_name = version + '-' + ctemplate.split('_')[0]
        kwargs.os_config_template = template_name
        if not kwargs.distributions.get(version):
            kwargs = kwargs | DotMap(
                api_filter=f"Version eq '{kwargs.os_version.name}'",
                build_skip=True,
                method='get',
                uri='hcl/OperatingSystems')
            kwargs = api('hcl_operating_system').calls(kwargs)
            kwargs.distributions[version].moid = kwargs.results[0].Moid
        kwargs.distribution_moid = kwargs.distributions[version].moid
        file_content = (open(os.path.join(answer), 'r')).read()
        for e in ['LayeredDriver:layered_driver',
                  'UILanguageFallback:secondary_language']:
            elist = e.split(':')
            rstring = '%s<%s>{{ .%s }}</%s>\n' % (
                " " * 12, elist[0], elist[1], elist[0])
            if kwargs.language[elist[1]] == '':
                file_content = file_content.replace(rstring, '')
        kwargs.file_content = file_content
        api_body = shared_functions.os_configuration_file(kwargs)
        existing = False
        for e in kwargs.os_cfg_results:
            if e.Name == api_body['Name'] and e.Distributions[0].Moid == kwargs.distribution_moid:
                existing = True
                kwargs.pmoid = e.Moid
                break
        kwargs = kwargs | DotMap(
            api_body=api_body,
            method='post',
            uri='os/ConfigurationFiles')
        if existing:
            kwargs.method = 'patch'
        kwargs = api('os_configuration').calls(kwargs)
        kwargs.os_cfg_moids[template_name] = DotMap(moid=kwargs.pmoid)
        kwargs.os_cfg_moid = kwargs.os_cfg_moids[template_name].moid
        if not existing:
            kwargs.os_cfg_results.append(kwargs.results)
            kwargs.os_cfg_moids = kwargs.os_cfg_moids | kwargs.pmoids
        else:
            indx = next(
                (index for (
                    index,
                    d) in enumerate(
                    kwargs.os_cfg_results) if d.Moid == kwargs.pmoid),
                None)
            kwargs.os_cfg_results[indx] = kwargs.results
        # =====================================================================
        # Return kwargs
        # =====================================================================
        return kwargs

    # =========================================================================
    # Function - OS Image Links
    # =========================================================================
    def os_image_links(self, kwargs):
        # Get Organization Software Repository Catalog
        kwargs = kwargs | DotMap(
            method='get',
            names=['user-catalog'],
            uri='softwarerepository/Catalogs')
        kwargs = api('org_catalog').calls(kwargs)
        catalog_moid = kwargs.pmoids['user-catalog'].moid
        # Get Organization Operating System Images
        kwargs = kwargs | DotMap(
            api_filter=f"Catalog.Moid eq '{catalog_moid}'",
            names=[],
            uri='softwarerepository/OperatingSystemFiles')
        kwargs = api('operating_system').calls(kwargs)
        kwargs.os_image_results = sorted(
            kwargs.results,
            key=itemgetter('CreateTime'),
            reverse=True)
        return kwargs

    # =========================================================================
    # Function - Vendor Operating Systems
    # =========================================================================
    def os_vendor_and_version(self, kwargs):
        org_moid = kwargs.org_moids[kwargs.org].moid
        kwargs = kwargs | DotMap(
            api_filter='ignore',
            method='get',
            uri='hcl/OperatingSystemVendors')
        kwargs = api('os_vendors').calls(kwargs)
        kwargs.os_vendors = kwargs.pmoids
        kwargs = kwargs | DotMap(
            api_filter='ignore',
            method='get',
            uri='hcl/OperatingSystems')
        kwargs = api('os_vendors').calls(kwargs)
        kwargs.os_versions = kwargs.pmoids
        kwargs = kwargs | DotMap(
            api_filter=f"Name in ('{kwargs.org_moids[kwargs.org].moid}','shared')",
            method='get',
            uri='os/Catalogs')
        kwargs = api('os_catalog').calls(kwargs)
        catalog_moids = kwargs.pmoids
        api_filter = f"Catalog.Moid in ('{catalog_moids[org_moid].moid}','{catalog_moids.shared.moid}')"
        kwargs = kwargs | DotMap(
            api_filter=api_filter,
            method='get',
            uri='os/ConfigurationFiles')
        kwargs = api('os_configuration').calls(kwargs)
        kwargs.org_catalog_moid = catalog_moids[org_moid].moid
        kwargs.os_cfg_moids = kwargs.pmoids
        kwargs.os_cfg_results = kwargs.results
        return kwargs

    # =========================================================================
    # Function - Build OS Install API Body
    # =========================================================================
    def os_install(self, kwargs):
        # =====================================================================
        # Load Variables and Send Begin Notification
        # =====================================================================
        notifications.section_begin_org(kwargs.org, self.type, 'Install')
        server_profiles = deepcopy(
            kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles)
        install_flag = False
        kwargs.models = sorted(
            list(numpy.unique(numpy.array([e.model for e in server_profiles]))))
        kwargs.org_moid = kwargs.org_moids[kwargs.org].moid
        os_install_fail_count = 0
        # =====================================================================
        # Get Physical Server Tags to Check for
        # Existing OS Install
        # =====================================================================
        kwargs = kwargs | DotMap(
            method='get',
            names=[
                e.serial for e in server_profiles],
            uri='compute/PhysicalSummaries')
        kwargs = api('serial_number').calls(kwargs)
        compute_moids = kwargs.pmoids
        boot_names = []
        os_cfg_moids = []
        for x in range(0, len(server_profiles)):
            v = kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x]
            kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].tags = compute_moids[server_profiles[x].serial].tags
            kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].os_installed = False
            boot_names.append(
                kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].boot_order.name)
            os_cfg_moids.append(
                kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].os_configuration)
            for e in compute_moids[v.serial].tags:
                if e.Key == 'os_installed' and e.Value == f'{v.os_vendor}: {v.os_version.name}':
                    kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].os_installed = True
                else:
                    install_flag = True
            if kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].boot_volume.lower(
            ) == 'm2':
                m2_found = False
                for k, v in kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].storage_controllers.items(
                ):
                    if re.search('MSTOR-RAID', v.slot):
                        m2_found = True
                        kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].virtual_drive = v.virtual_drives['0'].name
                if not m2_found:
                    pcolor.Red(f'\n{"-"*108}\n')
                    pcolor.Red(
                        f'  !!! ERROR !!!\n  Could not determine the Controller Slot for:')
                    pcolor.Red(f'  * Profile: {server_profiles[x].name}')
                    pcolor.Red(f'  * Serial:  {server_profiles[x].serial}')
                    pcolor.Red(
                        f'  Exiting... (intersight-tools/new/src/intersight/core.py Line 1448)')
                    pcolor.Red(f'\n{"-"*108}\n')
                    len(False)
                    sys.exit(1)
        # =====================================================================
        # Setup OS Settings for ezci
        # =====================================================================

        def sensitive_list_check(sensitive_list, kwargs):
            for e in sensitive_list:
                kwargs.sensitive_var = e
                kwargs = shared_functions.sensitive_var_value(kwargs)
                kwargs[e] = kwargs.var_value
            return kwargs
        # =====================================================================
        # Get Software Repository Data - If os_install is True
        # =====================================================================
        if install_flag:
            kwargs = system_software_repository(
                'os_cfg').os_configuration_files(kwargs)
            kwargs = system_software_repository('scu').scu_links(kwargs)
            for e in kwargs.os_cfg_results:
                kwargs.os_cfg_moids[e.Moid] = e
            for e in kwargs.scu_results:
                kwargs.scu[e.Moid] = e
        # =====================================================================
        # Deployment Type Customization
        # =====================================================================
        if install_flag and kwargs.script_name == 'ezci' and kwargs.args.deployment_type == 'azure_stack':
            kwargs.os_version = kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[0].os_version
            # kwargs = sensitive_list_check(['azure_stack_lcm_password', 'local_administrator_password'], kwargs)
            kwargs = sensitive_list_check(
                ['local_administrator_password'], kwargs)
            kwargs = system_software_repository(
                'azure_stack').os_cfg_azure_stack(kwargs)
            for x in range(0, len(
                    kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles)):
                kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].os_configuration = kwargs.os_cfg_moid
        elif install_flag and kwargs.script_name == 'ezci':
            kwargs = sensitive_list_check(['vmware_esxi_password'], kwargs)
        # =====================================================================
        # Install Operating System on Servers
        # =====================================================================
        count = 1
        for x in range(0, len(
                kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles)):
            v = kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x]
            if not v.os_installed:
                # =============================================================
                # Test Intersight Transition URL
                # =============================================================
                url = kwargs.scu[v.scu].Source.LocationLink
                if not kwargs.args.repository_check_skip:
                    shared_functions.test_repository_url(url)
                # =============================================================
                # Get Installation Interface
                # =============================================================
                if isinstance(v.install_interface, str):
                    for a, b in v.adapters.items():
                        vnic = [
                            DotMap(
                                name=c,
                                mac=d.mac_address,
                                slot=d.pci_slot) for c,
                            d in b.eth_ifs.items() if d.mac_address == v.install_interface][0]
                if v.boot_volume.lower() == 'san':
                    if count % 2 == 0:
                        kwargs.wwpn_index = 0
                        kwargs.san_target = v.boot_order.wwpn_targets[0]
                    else:
                        if len(v.boot_order.wwpn_targets) > 1:
                            kwargs.wwpn_index = 1
                            kwargs.san_target = v.boot_order.wwpn_targets[1]
                        else:
                            kwargs.wwpn_index = 0
                            kwargs.san_target = v.boot_order.wwpn_targets[0]
                    # kwargs.fc_ifs = [b for a,b in v.adapters[kwargs.san_target.slot].fc_ifs.items()]
                    kwargs.fc_ifs = v.adapters[kwargs.san_target.slot].fc_ifs
                    stgt = kwargs.san_target
                    pcolor.Green(f'\n{"-"*52}\n')
                    pcolor.Green(
                        f'\n{" "*2}- boot_mode: SAN\n{" "*5}boot_target:')
                    pcolor.Green(
                        f'{" "*4}initiator: {kwargs.fc_ifs[stgt.interface_name].wwpn}\n{" "*7}lun: {stgt.lun}\n{" "*7}target: {stgt.wwpn}')
                    pcolor.Green(
                        f'{" "*4}profile: {v.name}\n{" "*5}serial: {v.serial}')
                    pcolor.Green(
                        f'{" "*4}vnic:\n{" "*7}name: {vnic.name}\n{" "*7}mac: {vnic.mac}\n')
                elif v.boot_volume.lower() == 'm2' and isinstance(v.install_interface, str):
                    pcolor.Green(f'\n{"-"*52}\n')
                    pcolor.Green(f'{" "*2}- boot_mode: {v.boot_volume}')
                    pcolor.Green(
                        f'{" "*4}profile: {v.name}\n{" "*5}serial: {v.serial}')
                    pcolor.Green(
                        f'{" "*4}vnic:\n{" "*7}name: {vnic.name}\n{" "*7}mac: {vnic.mac}\n')
                else:
                    pcolor.Green(f'\n{"-"*52}\n')
                    pcolor.Green(f'{" "*2}- boot_mode: {v.boot_volume}')
                    pcolor.Green(
                        f'{" "*4}profile: {v.name}\n{" "*5}serial: {v.serial}')
                # =============================================================
                # POST OS Install
                # =============================================================
                kwargs = kwargs | DotMap(
                    api_body=shared_functions.installation_body(
                        v, kwargs), method='post', uri='os/Installs')
                kwargs = api(self.type).calls(kwargs)
                kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x].os_install = DotMap(
                    moid=kwargs.pmoid, workflow='')
        names = [e.os_install.moid for e in kwargs.imm_dict.orgs[kwargs.org]
                 .wizard.server_profiles if v.os_installed == False and len(e.os_install.moid) > 0]
        if install_flag:
            pcolor.Cyan(
                f'\n{"-" * 108}\n\n    Sleeping for 30 Minutes to pause for Workflow/Infos Lookup.')
            pcolor.Cyan(f'\n{"-" * 108}\n')
            time.sleep(1800)
        # =====================================================================
        # Monitor OS Installation until Complete
        # =====================================================================
        kwargs = kwargs | DotMap(method='get', names=names, uri='os/Installs')
        kwargs = api('moid_filter').calls(kwargs)
        install_pmoids = kwargs.pmoids
        install_results = kwargs.results
        for x in range(0, len(
                kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles)):
            v = kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x]
            indx = next((index for (index, d) in enumerate(
                install_results) if d['Moid'] == v.os_install.moid), None)
            v.install_success = False
            if indx is not None:
                v.os_install.workflow = install_results[indx].WorkflowInfo.Moid
                install_complete = False
                while install_complete == False:
                    kwargs = kwargs | DotMap(
                        method='get_by_moid',
                        pmoid=v.os_install.workflow,
                        uri='workflow/WorkflowInfos')
                    kwargs = api('workflow_info').calls(kwargs)
                    if kwargs.results.WorkflowStatus == 'Completed':
                        install_complete = True
                        v.install_success = True
                        pcolor.Green(
                            f'    - Completed Operating System Installation for `{v.name}`.')
                    elif re.search('Failed|Terminated|Canceled', kwargs.results.WorkflowStatus):
                        kwargs.upgrade.failed.update({v.name: v.moid})
                        pcolor.Red(
                            f'!!! ERROR !!! Failed Operating System Installation for Server Profile `{v.name}`.')
                        install_complete = True
                        os_install_fail_count += 1
                    else:
                        progress = kwargs.results.Progress
                        status = kwargs.results.WorkflowStatus
                        pcolor.Cyan(
                            f'{" "*6}* Operating System Installation for `{v.name}` still In Progress.'
                            f'  Status is: `{status}`, Progress is: {progress} Percent, Sleeping for 120 seconds.')
                        time.sleep(120)
                # =============================================================
                # Add os_installed Tag to Physical Server
                # =============================================================
                if v.install_success:
                    tags = deepcopy(v.tags)
                    tag_body = []
                    os_installed = False
                    for e in tags:
                        if e.Key == 'os_installed':
                            os_installed = True
                            tag_body.append(
                                {'Key': e.Key, 'Value': f'{v.os_vendor}: {v.os_version.name}'})
                        else:
                            tag_body.append(e.toDict())
                    if not os_installed:
                        tag_body.append(
                            {'Key': 'os_installed', 'Value': f'{v.os_vendor}: {v.os_version.name}'})
                    tags = list({d['Key']: d for d in tags}.values())
                    kwargs = kwargs | DotMap(
                        api_body={
                            'Tags': tag_body},
                        method='patch',
                        pmoid=v.hardware_moid,
                        tag_server_profile=v.name)
                    kwargs.uri = f'{v.object_type}s'.replace('.', '/')
                    kwargs = api('update_tags').calls(kwargs)
            elif v.os_installed == False:
                os_install_fail_count += 1
                pcolor.Red(
                    f'      * Something went wrong with the OS Install Request for {v.name}. Please Validate the Server.')
            else:
                pcolor.Cyan(
                    f'      * Skipping Operating System Install for {v.name}.')
        # =====================================================================
        # Send End Notification and return kwargs
        # =====================================================================
        notifications.section_end_org(kwargs.org, self.type, 'Install')
        if os_install_fail_count > 0:
            pcolor.Yellow(names)
            pcolor.Yellow(install_pmoids)
            pcolor.Yellow(json.dumps(install_results, indent=4))
            pcolor.Red(f'\n{"-"*108}\n')
            for x in range(0, len(
                    kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles)):
                v = kwargs.imm_dict.orgs[kwargs.org].wizard.server_profiles[x]
                if not v.install_success:
                    pcolor.Red(
                        f'      * OS Install Failed for `{v.name}`.  Please Validate the Logs.')
            pcolor.Red(f'\n{"-"*108}\n')
            pcolor.Red(
                f'  Exiting... (intersight-tools/new/src/intersight/core.py Line 1576)')
            len(False)
            sys.exit(1)
        return kwargs

    # =========================================================================
    # Function - SCU Links
    # =========================================================================
    def scu_links(self, kwargs):
        # Get Organization Software Repository Catalog
        kwargs = kwargs | DotMap(
            method='get',
            names=['user-catalog'],
            uri='softwarerepository/Catalogs')
        kwargs = api('org_catalog').calls(kwargs)
        catalog_moid = kwargs.pmoids['user-catalog'].moid
        # Get Organization Software Configuration Utility Repositories
        kwargs = kwargs | DotMap(
            api_filter=f"Catalog.Moid eq '{catalog_moid}'",
            names=[],
            uri='firmware/ServerConfigurationUtilityDistributables')
        kwargs = api('server_configuration_utility').calls(kwargs)
        kwargs.scu_results = sorted(
            kwargs.results,
            key=itemgetter('CreateTime'),
            reverse=True)
        return kwargs
