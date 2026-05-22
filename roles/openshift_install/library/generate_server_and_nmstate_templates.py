#!/usr/bin/env python3
"""Generate nmstate templates and assisted-installer/server.json from bare metal install vars."""
# pylint: disable=too-many-lines,duplicate-code

import base64
import binascii
import json
import os
import sys
import argparse
import re
import tarfile
import textwrap
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from ipaddress import ip_address, ip_interface
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from jinja2 import Environment, FileSystemLoader


SSH_PUBLIC_KEY_TYPE_PATTERN = re.compile(r"^(ssh-|ecdsa-|sk-)")

# Module-level sensitive schema properties, populated once by load_schema().
_SENSITIVE_SCHEMA_PROPS: Dict[str, Any] = {}

# Relative path from this file to the JSON schema.
_SCHEMA_PATH = Path(__file__).parent.parent.parent.parent / \
    "schema" / "cisco-ai-pods.json"


def load_schema() -> None:
    """Load abstract.sensitive_variables properties from the JSON schema into _SENSITIVE_SCHEMA_PROPS."""
    global _SENSITIVE_SCHEMA_PROPS  # pylint: disable=global-statement
    try:
        with open(_SCHEMA_PATH, encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
        definitions = schema.get("definitions", {})
        sensitive_def = definitions.get("abstract.sensitive_variables", {})
        _SENSITIVE_SCHEMA_PROPS = (
            sensitive_def.get("properties", {})
            if isinstance(sensitive_def, dict)
            else {}
        )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(
            f"Warning: Could not load schema for sensitive variable validation: {exc}")
        _SENSITIVE_SCHEMA_PROPS = {}


def _wrap_cli_text(text: Any, indent: str = "  ", width: int = 100) -> str:
    """Wrap long text blocks to keep CLI error output readable."""
    rendered = str(text) if text not in (None, "") else "N/A"
    return textwrap.fill(
        rendered,
        width=width,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _format_sensitive_constraints(context_label: str, schema_rule: Any) -> str:
    """Build a wrapped, human-readable constraint block for error messages."""
    if not isinstance(schema_rule, dict):
        return ""
    description = schema_rule.get("description", "N/A")
    pattern = schema_rule.get("pattern", "N/A")
    min_length = schema_rule.get("minLength", "N/A")
    max_length = schema_rule.get("maxLength", "N/A")
    return (
        f"\n\nSensitive Variable Constraints for '{context_label}':\n"
        f"Description:\n{_wrap_cli_text(description)}\n"
        f"Pattern:\n{_wrap_cli_text(pattern)}\n"
        f"Min Length: {min_length}\n"
        f"Max Length: {max_length}"
    )


def _validate_sensitive_value(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    value: Any,
    schema_rule: Any,
    env_var_name: str,
    context: str,
    schema_key: Optional[str] = None,
    sensitive_properties: Optional[Dict[str, Any]] = None,
) -> None:
    """Validate a resolved sensitive value against schema minLength/maxLength/pattern."""
    if value in (None, ""):
        error_msg = (
            f"Missing required environment variable '{env_var_name}' for {context}.\n"
            f"\n  To fix this, run:\n"
            f"    export {env_var_name}='<your_value_here>'")
        if schema_key and sensitive_properties and schema_key in sensitive_properties:
            error_msg += _format_sensitive_constraints(
                schema_key, sensitive_properties[schema_key])
        raise ValueError(error_msg)

    if not isinstance(schema_rule, dict):
        return

    text_value = str(value)
    min_length = schema_rule.get("minLength")
    max_length = schema_rule.get("maxLength")
    pattern = schema_rule.get("pattern")
    constraint_info = _format_sensitive_constraints(context, schema_rule)

    if isinstance(min_length, int) and len(text_value) < min_length:
        raise ValueError(
            f"Environment variable '{env_var_name}' for {context} is too short "
            f"({len(text_value)} < {min_length}). Value is sensitive and hidden."
            f"{constraint_info}")
    if isinstance(max_length, int) and len(text_value) > max_length:
        raise ValueError(
            f"Environment variable '{env_var_name}' for {context} is too long "
            f"({len(text_value)} > {max_length}). Value is sensitive and hidden."
            f"{constraint_info}")
    if isinstance(pattern, str) and pattern:
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            raise ValueError(
                f"Invalid regex pattern in abstract.sensitive_variables for {context}: {exc}"
            ) from exc
        if compiled.search(text_value) is None:
            raise ValueError(
                f"Environment variable '{env_var_name}' for {context} does not match "
                f"the schema pattern. Value is sensitive and hidden."
                f"{constraint_info}")


def _resolve_sensitive_identifier(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    var_id: Any,
    env_prefix: str,
    schema_key: Optional[str],
    context: str,
    sensitive_properties: Dict[str, Any],
    resolved_vars: Dict[str, str],
) -> None:
    """Resolve one sensitive variable identifier to its env value and validate.

    Args:
        var_id:               Integer identifier from the model (1-64).
        env_prefix:           Environment variable name prefix (without _N suffix).
        schema_key:           Key inside abstract.sensitive_variables for validation rules,
                              or None if no schema entry exists.
        context:              Human-readable path used in error messages.
        sensitive_properties: Dict returned by accessing _SENSITIVE_SCHEMA_PROPS.
        resolved_vars:        Mutable dict where resolved env_var_name -> value is stored.
    """
    if var_id in (None, ""):
        return
    if not isinstance(var_id, int) or var_id <= 0:
        raise ValueError(
            f"{context} must be a positive integer sensitive variable identifier."
        )

    env_var_name = f"{env_prefix}_{var_id}"
    env_value = os.environ.get(env_var_name)
    if env_value in (None, ""):
        error_msg = (
            f"Missing required environment variable '{env_var_name}' for {context}.\n"
            f"\n  To fix this, run:\n"
            f"    export {env_var_name}='<your_value_here>'")
        if schema_key and schema_key in sensitive_properties:
            error_msg += _format_sensitive_constraints(
                schema_key, sensitive_properties[schema_key])
        raise ValueError(error_msg)

    if schema_key:
        schema_rule = sensitive_properties.get(schema_key, {})
        _validate_sensitive_value(
            env_value, schema_rule, env_var_name, context,
            schema_key, sensitive_properties,
        )

    resolved_vars[env_var_name] = str(env_value)


def _resolve_sensitive_var(
    var_id: Any,
    env_prefix: str,
    schema_key: Optional[str],
    context: str,
) -> str:
    """Resolve and validate one sensitive variable, returning its value.

    Thin wrapper around _resolve_sensitive_identifier that returns the resolved
    string value directly rather than writing into a shared dict.
    """
    resolved: Dict[str, str] = {}
    _resolve_sensitive_identifier(
        var_id, env_prefix, schema_key, context,
        _SENSITIVE_SCHEMA_PROPS, resolved,
    )
    env_var_name = f"{env_prefix}_{var_id}"
    return resolved[env_var_name]


def merge_dicts(base: Dict[str, Any],
                new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries, with new_data taking precedence."""
    merged = dict(base)
    for key, value in new_data.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_yaml_mapping(vars_file: Path) -> Dict[str, Any]:
    """Load a YAML file containing a top-level mapping."""
    try:
        with open(vars_file, "r", encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle)
    except FileNotFoundError:
        print(f"Error: vars file not found: {vars_file}")
        sys.exit(1)
    except yaml.YAMLError as error:
        print(f"Error parsing YAML: {error}")
        sys.exit(1)

    if not isinstance(data, dict):
        print(
            f"Error: vars file must contain a top-level mapping: {vars_file}")
        sys.exit(1)

    return data


def load_vars_path(vars_path: Path) -> Dict[str, Any]:
    """Load a vars file or recursively merge all YAML files from a vars directory."""
    if vars_path.is_file():
        return load_yaml_mapping(vars_path)

    if not vars_path.exists():
        print(f"Error: vars path not found: {vars_path}")
        sys.exit(1)

    if not vars_path.is_dir():
        print(f"Error: vars path must be a file or directory: {vars_path}")
        sys.exit(1)

    vars_files = sorted(
        [*vars_path.glob("*.yml"), *vars_path.glob("*.yaml")],
        key=lambda path: path.name,
    )
    if not vars_files:
        print(f"Error: no YAML vars files found in: {vars_path}")
        sys.exit(1)

    merged: Dict[str, Any] = {}
    for vars_file in vars_files:
        merged = merge_dicts(merged, load_yaml_mapping(vars_file))
    return merged


def get_bare_metal_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return openshift.install.bare_metal configuration."""
    return config.get("openshift", {}).get("install", {}).get("bare_metal", {})


def get_servers(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return server list from openshift.install.bare_metal.servers."""
    servers = get_bare_metal_config(config).get("servers", [])
    return servers if isinstance(servers, list) else []


def get_dns_servers(config: Dict[str, Any]) -> List[str]:
    """Return configured DNS servers or a default pair."""
    dns_servers = get_bare_metal_config(config).get(
        "cluster_networking", {}).get(
        "dns_servers", [])
    return dns_servers if dns_servers else ["8.8.8.8", "8.8.4.4"]


def get_cluster_routes(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return bare metal cluster routes."""
    routes = get_bare_metal_config(config).get(
        "cluster_networking", {}).get(
        "routes", [])
    return routes if isinstance(routes, list) else []


def get_ssh_public_key_suffix(config: Dict[str, Any]) -> Any:
    """Return the SSH public key sensitive variable suffix."""
    return get_bare_metal_config(config).get("ssh_public_key")


def determine_template_type(server: Dict[str, Any]) -> Optional[str]:
    """Return template type from nested server interface definitions."""
    interfaces = server.get("interfaces", {})
    if interfaces.get("bond"):
        return "bond"
    if interfaces.get("ethernet"):
        return "ethernet"
    return None


def get_bond_members(bond: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return normalized bond member list supporting old and new field names."""
    members = bond.get("interfaces")
    if members is None:
        members = bond.get("intfaces", [])
    return members if isinstance(members, list) else []


def get_first_interface_ip(server: Dict[str, Any]) -> Optional[str]:
    """Return the first interface IP without CIDR suffix."""
    template_type = determine_template_type(server)
    if template_type == "ethernet":
        interfaces = server.get("interfaces", {}).get("ethernet", [])
        if interfaces:
            return str(interfaces[0].get('ipv4', '')).split('/', maxsplit=1)[0] or None
    if template_type == "bond":
        bonds = server.get("interfaces", {}).get("bond", [])
        if bonds:
            return str(bonds[0].get('ipv4', '')).split('/', maxsplit=1)[0] or None
    return None


def applicable_routes(interface_ipv4: str,
                      cluster_routes: List[Dict[str,
                                                str]]) -> List[Dict[str,
                                                                    str]]:
    """Return routes whose gateway is on the same network as the interface IP."""
    if not interface_ipv4:
        return []

    try:
        network = ip_interface(interface_ipv4).network
    except ValueError:
        return []

    matched_routes: List[Dict[str, str]] = []
    for route in cluster_routes:
        destination = route.get("destination")
        gateway = route.get("gateway")
        if not destination or not gateway:
            continue
        try:
            if ip_address(gateway) in network:
                matched_routes.append(
                    {"destination": destination, "gateway": gateway})
        except ValueError:
            continue
    return matched_routes


def extract_ethernet_groups(server: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize ethernet interfaces into grouped template objects."""
    groups: List[Dict[str, Any]] = []
    for index, interface in enumerate(
        server.get(
            "interfaces", {}).get(
            "ethernet", []), 1):
        groups.append(
            {
                "group": index,
                "name": interface.get("name", f"eth{index - 1}"),
                "mac": interface.get("mac", ""),
                "ipv4": interface.get("ipv4", ""),
                "mtu": interface.get("mtu", 9000),
                "lldp_enabled": interface.get("lldp_enabled", True),
            }
        )
    return groups


def extract_bond_groups(server: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize bond interfaces into grouped template objects."""
    groups: List[Dict[str, Any]] = []
    for index, bond in enumerate(
        server.get(
            "interfaces", {}).get(
            "bond", []), 1):
        groups.append(
            {
                "group": index,
                "name": bond.get("name", f"bond{index - 1}"),
                "ipv4": bond.get("ipv4", ""),
                "mtu": bond.get("mtu", 9000),
                "lldp_enabled": bond.get("lldp_enabled", True),
                "members": get_bond_members(bond),
            }
        )
    return groups


def build_route_entries(
        groups: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build route loop context for nmstate templates."""
    route_entries: List[Dict[str, Any]] = []
    cluster_routes = get_cluster_routes(config)
    for group in groups:
        routes = applicable_routes(group.get("ipv4", ""), cluster_routes)
        for route_index, _route in enumerate(routes, 1):
            route_entries.append(
                {"group": group["group"], "route_index": route_index})
    return route_entries


def build_ethernet_context(
        server: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Build Jinja context for ethernet nmstate template."""
    groups = extract_ethernet_groups(server)
    return {
        "interface": [{"group": group["group"]} for group in groups],
        "route_entries": build_route_entries(groups, config),
        "dns_servers": get_dns_servers(config),
    }


def build_bond_context(
        server: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Build Jinja context for bond nmstate template."""
    bond_groups = extract_bond_groups(server)
    physical_interfaces: List[Dict[str, Any]] = []
    interfaces: List[Dict[str, Any]] = []

    for group in bond_groups:
        member_indices: List[int] = []
        for member_index, _member in enumerate(group.get("members", []), 1):
            physical_interfaces.append(
                {"group": group["group"], "member": member_index})
            member_indices.append(member_index)
        interfaces.append(
            {"group": group["group"], "member_indices": member_indices})

    return {
        "physical_interfaces": physical_interfaces,
        "interfaces": interfaces,
        "route_entries": build_route_entries(bond_groups, config),
        "dns_servers": get_dns_servers(config),
    }


def render_jinja_template(env: Environment,
                          template_name: str,
                          context: Dict[str,
                                        Any]) -> Optional[str]:
    """Render and normalize a Jinja template."""
    try:
        template = env.get_template(template_name)
        rendered = template.render(context)
    except (Exception) as error:  # pylint: disable=broad-exception-caught
        print(f"Error rendering template {template_name}: {error}")
        return None

    lines = [line.rstrip() for line in rendered.splitlines()]
    lines = [line for line in lines if line.strip()]
    return "\n".join(lines) + "\n"


def build_profile(
        server: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a stable profile for unique nmstate generation."""
    template_type = determine_template_type(server)
    if not template_type:
        return None

    cluster_routes = get_cluster_routes(config)
    if template_type == "ethernet":
        groups = extract_ethernet_groups(server)
        route_shape = tuple(len(applicable_routes(
            group.get("ipv4", ""), cluster_routes)) for group in groups)
        key: Tuple[Any, ...] = (template_type, len(groups), route_shape)
        route_suffix = "-".join(str(item)
                                for item in route_shape) if route_shape else "0"
        filename = f"nmstate_ethernet_{len(groups)}_r{route_suffix}.yaml"
        template_name = "iserver-nmstate-ethernet.yaml.j2"
        context = build_ethernet_context(server, config)
    else:
        groups = extract_bond_groups(server)
        member_shape = tuple(len(group.get("members", [])) for group in groups)
        route_shape = tuple(len(applicable_routes(
            group.get("ipv4", ""), cluster_routes)) for group in groups)
        key = (template_type, len(groups), member_shape, route_shape)
        member_suffix = "-".join(str(item)
                                 for item in member_shape) if member_shape else "0"
        route_suffix = "-".join(str(item)
                                for item in route_shape) if route_shape else "0"
        filename = f"nmstate_bond_{len(groups)}_m{member_suffix}_r{route_suffix}.yaml"
        template_name = "iserver-nmstate-bond.yaml.j2"
        context = build_bond_context(server, config)

    return {
        "key": key,
        "filename": filename,
        "template_name": template_name,
        "context": context}


def generate_unique_nmstate_templates(
    servers: List[Dict[str, Any]],
    config: Dict[str, Any],
    output_dir: Path,
    env: Environment,
) -> Dict[int, str]:
    """Generate one nmstate file per unique interface profile."""
    profile_to_filename: Dict[Tuple[Any, ...], str] = {}
    server_to_filename: Dict[int, str] = {}

    for index, server in enumerate(servers):
        hostname = server.get("hostname", "unknown")
        profile = build_profile(server, config)
        if not profile:
            print(
                f"Warning: Could not determine nmstate profile for {hostname}")
            continue

        key = profile["key"]
        if key not in profile_to_filename:
            content = render_jinja_template(
                env, profile["template_name"], profile["context"])
            if not content:
                print(f"Warning: Failed to render nmstate for {hostname}")
                continue
            file_path = output_dir / profile["filename"]
            file_path.write_text(content, encoding="utf-8")
            profile_to_filename[key] = profile["filename"]
            print(f"Generated unique template: {file_path}")

        server_to_filename[index] = profile_to_filename[key]

    return server_to_filename


def cleanup_existing_nmstate_templates(output_dir: Path) -> None:
    """Remove previously generated nmstate templates."""
    for file_path in output_dir.glob("nmstate_*.yaml"):
        file_path.unlink(missing_ok=True)


def validate_ssh_public_key_value(value: str, context: str) -> None:
    """Validate that a value looks like an SSH public key."""
    parts = value.strip().split()
    if len(parts) < 2:
        raise ValueError(
            f"Invalid SSH public key for {context}: expected '<type> <base64> [comment]'")

    key_type, key_data = parts[0], parts[1]
    if not SSH_PUBLIC_KEY_TYPE_PATTERN.match(key_type):
        raise ValueError(
            f"Invalid SSH public key type for {context}: {key_type}")

    try:
        base64.b64decode(key_data.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError) as error:
        raise ValueError(
            f"Invalid SSH public key payload for {context}") from error


def resolve_ssh_public_key(config: Dict[str, Any]) -> str:
    """Resolve and validate the SSH public key from its sensitive variable suffix."""
    suffix = get_ssh_public_key_suffix(config)
    value = _resolve_sensitive_var(
        suffix,
        "ssh_public_key",
        "ssh_public_key",
        "openshift.install.bare_metal.ssh_public_key",
    )
    validate_ssh_public_key_value(value, f"ssh_public_key_{suffix}")
    return value


def collect_required_credential_env_vars(
        servers: List[Dict[str, Any]], config: Dict[str, Any]) -> Tuple[Set[str], List[str]]:
    """Collect required credential env var names and configuration issues."""
    required_env_vars: Set[str] = set()
    config_issues: List[str] = []

    ssh_public_key_suffix = get_ssh_public_key_suffix(config)
    if ssh_public_key_suffix in (None, ""):
        config_issues.append(
            "missing openshift.install.bare_metal.ssh_public_key sensitive variable suffix")
    else:
        required_env_vars.add(f"ssh_public_key_{ssh_public_key_suffix}")

    for server in servers:
        hostname = server.get("hostname", "unknown-host")

        if server.get("fabric_interconnect"):
            fi_ref = server.get("fabric_interconnect", {})
            fi_entry = resolve_fabric_interconnect(fi_ref, config)
            if not fi_entry:
                config_issues.append(
                    f"host {hostname}: unable to resolve fabric_interconnect reference {fi_ref.get('id')}"
                )
                continue
            suffix = fi_entry.get("password")
            if suffix in (None, ""):
                config_issues.append(
                    f"host {hostname}: missing fabric_interconnect password suffix for endpoint {fi_entry.get('ip', '')}"
                )
                continue
            required_env_vars.add(f"fabric_interconnect_password_{suffix}")
            continue

        if server.get("redfish"):
            redfish = server.get("redfish", {})
            suffix = redfish.get("password")
            if suffix in (None, ""):
                config_issues.append(
                    f"host {hostname}: missing redfish password suffix for endpoint {redfish.get('ip', redfish.get('endpoint_ip', ''))}"
                )
                continue
            required_env_vars.add(f"redfish_password_{suffix}")

    return required_env_vars, config_issues


def validate_credential_env_vars(
        servers: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    """Fail fast with a complete list of missing credential env vars."""
    required_env_vars, config_issues = collect_required_credential_env_vars(
        servers, config)
    missing_env_vars = sorted(
        env_name for env_name in required_env_vars if not os.getenv(env_name))

    ssh_key_issue: Optional[str] = None
    if not config_issues and not missing_env_vars:
        try:
            resolve_ssh_public_key(config)
        except ValueError as error:
            ssh_key_issue = str(error)

    if not config_issues and not missing_env_vars and not ssh_key_issue:
        return

    print("Error: credential environment variable validation failed")
    if config_issues:
        print("Configuration issues:")
        for issue in config_issues:
            print(f"  - {issue}")
    if missing_env_vars:
        print("Missing environment variables:")
        for env_name in missing_env_vars:
            print(f"  - {env_name}")
    if ssh_key_issue:
        print("SSH public key issue:")
        print(f"  - {ssh_key_issue}")
    sys.exit(1)


def generate_ssh_public_key_file(
        output_dir: Path, config: Dict[str, Any]) -> bool:
    """Generate assisted-installer/ssh.pub from the SSH public key environment variable."""
    ssh_public_key = resolve_ssh_public_key(config)
    file_path = output_dir / "ssh.pub"
    try:
        file_path.write_text(f"{ssh_public_key.rstrip()}\n", encoding="utf-8")
        print(f"Generated: {file_path}")
        return True
    except IOError as error:
        print(f"Error writing {file_path}: {error}")
        return False


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate nmstate templates and assisted-installer/server.json from bare metal install vars.")
    parser.add_argument(
        "--vars-file",
        type=Path,
        help="Path to a vars YAML file or a directory of vars files. Defaults to ../script_vars/.",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help=(
            "Validate required fi_password_<suffix> and redfish_password_<suffix> "
            "environment variables and exit without generating files."),
    )
    return parser.parse_args()


def _github_request(url: str) -> Any:
    """Perform a GitHub API request with optional token auth."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "iserver-installer-generator",
    }
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    request = Request(url, headers=headers)
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def _safe_extract_tar(archive_path: Path, destination: Path) -> None:
    """Safely extract tar.gz contents into destination directory."""
    destination_resolved = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as tar_handle:
        for member in tar_handle.getmembers():
            member_path = (destination / member.name).resolve()
            if os.path.commonpath([str(destination_resolved), str(
                    member_path)]) != str(destination_resolved):
                raise ValueError(
                    f"Unsafe path in archive member: {member.name}")
        tar_handle.extractall(destination)


def download_and_extract_latest_iserver_release(output_dir: Path) -> None:  # pylint: disable=too-many-locals
    """Download latest Linux tar.gz release asset from datacenter/iserver and extract it.

    If an iServer Linux tar.gz already exists in the output directory, skip downloading
    and extract from the existing local archive.
    """
    existing_archives = sorted(path for path in output_dir.glob(
        "*.tar.gz") if "iserver" in path.name.lower() and "linux" in path.name.lower())

    if existing_archives:
        archive_path = existing_archives[0]
        print(f"Using existing iServer Linux archive: {archive_path}")
    else:
        release_api = "https://api.github.com/repos/datacenter/iserver/releases/latest"
        try:
            release_data = _github_request(release_api)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(
                f"Failed to fetch latest release metadata from {release_api}: {error}") from error

        assets = release_data.get("assets", [])
        linux_tar_asset = None
        for asset in assets:
            name = str(asset.get("name", "")).lower()
            if "linux" in name and name.endswith(".tar.gz"):
                linux_tar_asset = asset
                break

        if not linux_tar_asset:
            raise RuntimeError(
                "No Linux .tar.gz asset found in latest datacenter/iserver release")

        download_url = linux_tar_asset.get("browser_download_url")
        asset_name = linux_tar_asset.get("name", "iserver-linux.tar.gz")
        if not download_url:
            raise RuntimeError(
                "Latest release Linux asset is missing browser_download_url")

        archive_path = output_dir / asset_name
        try:
            headers = {"User-Agent": "iserver-installer-generator"}
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                headers["Authorization"] = f"Bearer {github_token}"

            request = Request(download_url, headers=headers)
            with urlopen(request, timeout=120) as response, open(archive_path, "wb") as file_handle:
                file_handle.write(response.read())
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(
                f"Failed to download asset {asset_name}: {error}") from error

        print(
            f"Downloaded latest iServer Linux release archive: {archive_path}")

    try:
        _safe_extract_tar(archive_path, output_dir)
    except (tarfile.TarError, ValueError) as error:
        raise RuntimeError(
            f"Failed to extract asset {archive_path}: {error}") from error

    print(f"Extracted iServer Linux release asset into: {output_dir}")


def resolve_fabric_interconnect(
        fi_ref: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve fabric interconnect reference against bare metal fabric_interconnects list."""
    fabric_interconnects = get_bare_metal_config(
        config).get("fabric_interconnects", [])
    identifier = fi_ref.get("id")

    if isinstance(identifier, int):
        if 0 <= identifier < len(fabric_interconnects):
            return fabric_interconnects[identifier]
        if 1 <= identifier <= len(fabric_interconnects):
            return fabric_interconnects[identifier - 1]

    if isinstance(identifier, str):
        for entry in fabric_interconnects:
            if str(entry.get("ip")) == identifier:
                return entry
        if identifier.isdigit():
            index_value = int(identifier)
            if 0 <= index_value < len(fabric_interconnects):
                return fabric_interconnects[index_value]
            if 1 <= index_value <= len(fabric_interconnects):
                return fabric_interconnects[index_value - 1]

    return {}


def resolve_redfish(
        server: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build redfish dictionary for server.json."""
    hostname = server.get("hostname", "unknown-host")

    if server.get("fabric_interconnect"):
        fi_ref = server.get("fabric_interconnect", {})
        fi_entry = resolve_fabric_interconnect(fi_ref, config)
        if not fi_entry:
            return None
        return {
            "endpoint_ip": fi_entry.get(
                "ip",
                ""),
            "endpoint_type": "fi",
            "inventory_id": fi_ref.get(
                "inventory_id",
                ""),
            "password": _resolve_sensitive_var(
                fi_entry.get("password"),
                "fabric_interconnect_password",
                "fabric_interconnect_password",
                f"host {hostname} fabric_interconnect {fi_entry.get('ip', '')}",
            ),
            "username": fi_entry.get(
                "username",
                ""),
        }

    if server.get("redfish"):
        redfish = server.get("redfish", {})
        return {
            "endpoint_ip": redfish.get("endpoint_ip", redfish.get("ip", "")),
            "endpoint_type": redfish.get("endpoint_type", redfish.get("type", "bmc")),
            "password": _resolve_sensitive_var(
                redfish.get("password"),
                "redfish_password",
                "redfish_password",
                f"host {hostname} redfish endpoint {redfish.get('ip', redfish.get('endpoint_ip', ''))}",
            ),
            "username": redfish.get("username", ""),
        }

    return None


def build_server_interfaces_and_groups(
        server: Dict[str, Any], config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build assisted-installer interface and group arrays from nested server definitions."""
    template_type = determine_template_type(server)
    interface_entries: List[Dict[str, Any]] = []
    group_entries: List[Dict[str, Any]] = []
    cluster_routes = get_cluster_routes(config)

    if template_type == "ethernet":
        groups = extract_ethernet_groups(server)
        for group in groups:
            interface_entries.append({"name": group["name"], "mac": str(
                group.get("mac", "")).lower(), "group": group["group"]})
            group_entry: Dict[str, Any] = {
                "id": group["group"], "ip": group.get("ipv4", "")}
            routes = applicable_routes(group.get("ipv4", ""), cluster_routes)
            if routes:
                group_entry["route"] = [
                    {"cidr": route["destination"], "nh": route["gateway"]} for route in routes]
            group_entries.append(group_entry)
    elif template_type == "bond":
        groups = extract_bond_groups(server)
        for group in groups:
            for member in group.get("members", []):
                interface_entries.append(
                    {
                        "name": member.get("name", ""),
                        "mac": str(member.get("mac", "")).lower(),
                        "group": group["group"],
                    }
                )
            group_entry = {"id": group["group"], "ip": group.get("ipv4", "")}
            routes = applicable_routes(group.get("ipv4", ""), cluster_routes)
            if routes:
                group_entry["route"] = [
                    {"cidr": route["destination"], "nh": route["gateway"]} for route in routes]
            group_entries.append(group_entry)

    return interface_entries, group_entries


def normalize_server_for_output(
        server: Dict[str, Any], nmstate_filename: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one server into assisted-installer/server.json format."""
    server_obj: Dict[str, Any] = {"hostname": server.get(
        "hostname"), "role": server.get("role", "worker")}

    if "rendezvous" in server:
        server_obj["kube"] = server.get("rendezvous")

    redfish = resolve_redfish(server, config)
    if redfish:
        server_obj["redfish"] = redfish

    first_ip = get_first_interface_ip(server)
    if first_ip:
        server_obj["ssh"] = {"ip": first_ip}

    server_obj["vlan"] = server.get("vlan", 0)

    interface_entries, group_entries = build_server_interfaces_and_groups(
        server, config)
    server_obj["interface"] = interface_entries
    server_obj["group"] = group_entries
    server_obj["nmstate"] = nmstate_filename
    return server_obj


def generate_server_json(
    servers: List[Dict[str, Any]],
    server_to_filename: Dict[int, str],
    output_dir: Path,
    config: Dict[str, Any],
) -> bool:
    """Generate assisted-installer/server.json from server definitions and nmstate mapping."""
    output_data: List[Dict[str, Any]] = []

    for index, server in enumerate(servers):
        nmstate_filename = server_to_filename.get(index)
        if not nmstate_filename:
            continue
        output_data.append(
            normalize_server_for_output(
                server, nmstate_filename, config))

    file_path = output_dir / "server.json"
    try:
        with open(file_path, "w", encoding="utf-8") as file_handle:
            json.dump(output_data, file_handle, indent=4)
        print(f"Generated: {file_path}")
        return True
    except IOError as error:
        print(f"Error writing {file_path}: {error}")
        return False


def main() -> None:  # pylint: disable=too-many-statements
    """Parse arguments, load config, and generate nmstate/server templates."""
    args = parse_args()
    load_schema()

    script_dir = Path(__file__).parent
    vars_path = args.vars_file if args.vars_file else script_dir.parent / "script_vars"
    output_dir = script_dir / "assisted-installer"
    templates_dir = script_dir / "templates"

    if not templates_dir.exists():
        print(f"Error: templates directory not found: {templates_dir}")
        sys.exit(1)

    config = load_vars_path(vars_path)
    servers = get_servers(config)
    if not servers:
        print("Error: No servers found in openshift.install.bare_metal.servers")
        sys.exit(1)

    validate_credential_env_vars(servers, config)

    if args.check_env:
        print("Environment validation passed")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        download_and_extract_latest_iserver_release(output_dir)
    except RuntimeError as error:
        print(f"Error: {error}")
        sys.exit(1)

    env = Environment(loader=FileSystemLoader(str(templates_dir)))

    print(f"Loading configuration from: {vars_path}")
    print(f"Found {len(servers)} server(s) in configuration")

    cleanup_existing_nmstate_templates(output_dir)
    server_to_filename = generate_unique_nmstate_templates(
        servers, config, output_dir, env)
    print(
        f"Mapped {len(server_to_filename)} server(s) to nmstate template profiles")

    print("Generating ssh.pub...", end=" ")
    try:
        if generate_ssh_public_key_file(output_dir, config):
            print("✓")
        else:
            print("✗")
            sys.exit(1)
    except ValueError as error:
        print("✗")
        print(f"Error: {error}")
        sys.exit(1)

    print("Generating server.json...", end=" ")
    try:
        if generate_server_json(
                servers,
                server_to_filename,
                output_dir,
                config):
            print("✓")
        else:
            print("✗")
    except ValueError as error:
        print("✗")
        print(f"Error: {error}")
        sys.exit(1)

    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
