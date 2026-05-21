# OpenShift Install — Manifest Generation

This directory contains an Ansible playbook and supporting files to generate the manifests needed to deploy a bare-metal OpenShift cluster via **Cisco iServer** and the **OpenShift Assisted Installer**. It also includes a Python module for generating more complex output artifacts.

**Back to OpenShift README:** [OpenShift Deployment Order](../README.md)

## Table of Contents

- [OpenShift Install — Manifest Generation](#openshift-install--manifest-generation)
  - [Table of Contents](#table-of-contents)
  - [Directory Structure](#directory-structure)
  - [Prerequisites](#prerequisites)
  - [Playbook Features & Improvements](#playbook-features--improvements)
  - [Quick Start](#quick-start)
  - [Re-running the Playbook](#re-running-the-playbook)
  - [Variables Reference](#variables-reference)
    - [`openshift.install.bare_metal`](#openshiftinstallbare_metal)
    - [`fabric_interconnects[]`](#fabric_interconnects)
    - [`iso_web_server`](#iso_web_server)
    - [`servers[]`](#servers)
    - [`openshift.operators`](#openshiftoperators)
    - [`proxy` (optional)](#proxy-optional)
  - [Feature Flags](#feature-flags)
  - [Generated Output](#generated-output)
  - [Troubleshooting](#troubleshooting)
  - [Acknowledgments](#acknowledgments)
  - [Security Notes](#security-notes)

---

## Directory Structure

```
openshift/
├── examples/
│   ├── install.ezai.yaml                    # Example install variables file to copy
│   └── operators.ezai.yaml                  # Example operators variables file to copy
├── script_vars/
│   ├── install.ezai.yaml                    # Active install variables consumed by this module
│   └── operators.ezai.yaml                  # Active operators variables merged by this module
└── install/
  ├── create_install_manifest_files.yaml   # Main Ansible playbook
  ├── generate_server_and_nmstate_templates.py  # Python module for complex assisted-installer output generation
  ├── tasks/
  │   ├── cilium.yaml                      # Cilium CNI manifest tasks
  │   ├── persistent_net_rules.yaml        # NVIDIA Network Operator udev rule tasks
  │   └── proxy.yaml                       # HTTP/HTTPS proxy manifest tasks
  ├── templates/                           # Jinja2 templates
  │   ├── cilium-config.yaml.j2            # CiliumConfig custom resource
  │   ├── cilium-network.yaml.j2           # Cluster network config (kube-proxy replacement)
  │   ├── cilium-subscription.yaml.j2      # Cilium operator subscription
  │   ├── iserver-cluster.json.j2          # iServer cluster manifest
  │   ├── iserver-proxy.json.j2            # iServer proxy manifest
  │   ├── iserver-web.json.j2              # iServer ISO web server manifest
  │   ├── 70-machine-config-udev-network.yaml.j2
  │   ├── 70-persistent-net.rules.j2
  │   ├── 99-kernel-arguments.yaml.j2
  │   ├── 99-kubelet-config-memory.yaml.j2
  │   ├── 99-node-disruption-policy.j2
  │   ├── 99-nvme-nqn-generate.yaml.j2
  │   └── 99-portworx-multipathd-config.yaml.j2
  └── assisted-installer/                  # Generated output directory
    ├── cluster.json
    ├── ssh.pub
    ├── web_server.json
    └── manifests/                       # OpenShift manifests for Assisted Installer
```

[Back to Table of Contents](#table-of-contents)

---

## Prerequisites

- Ansible installed with the following collections:
  - `ansible.builtin`
  - `community.general` (for `json_query` filter)
- Use the iServer executable downloaded from the datacenter/iserver GitHub releases to manage the target UCS Server inventory
- An ISO web server reachable from the target nodes
- An SSH key pair for cluster node access

[Back to Table of Contents](#table-of-contents)

---

## Playbook Features & Improvements

`create_install_manifest_files.yaml` now includes:

- Recursive merge loading from `../script_vars/*.yml|*.yaml`
- Required install structure validation before manifest generation
- SSH public key resolution from sensitive environment variables (`ssh_public_key_<suffix>`) instead of file path lookup
- Validation that required SSH key environment variables are set before writing `assisted-installer/ssh.pub`

These updates align the Ansible manifest generator with the Python generator's sensitive variable model.

[Back to Table of Contents](#table-of-contents)

---

## Quick Start

1. **Create the shared vars folder if needed, then copy the required example variable files** and populate them with your environment's values:

   ```bash
  mkdir -p ../script_vars
  cp ../examples/install.ezai.yaml ../script_vars/install.ezai.yaml
  cp ../examples/operators.ezai.yaml ../script_vars/operators.ezai.yaml
   ```

2. **Edit `../script_vars/install.ezai.yaml` and `../script_vars/operators.ezai.yaml`** — at a minimum configure:
   - `openshift.install.bare_metal.cluster_name`
   - `openshift.install.bare_metal.base_dns_domain`
   - `openshift.install.bare_metal.cluster_version`
   - `openshift.install.bare_metal.cluster_networking` (API VIP, Ingress VIP, machine network, DNS)
   - `openshift.install.bare_metal.fabric_interconnects` (iServer inventory, if using servers with `fabric_interconnect`)
   - `openshift.install.bare_metal.iso_web_server` (IP, image URL, upload directory)
   - `openshift.install.bare_metal.servers` (hostnames, roles, interfaces, MACs)
  - `openshift.operators` settings required for install-time generated manifests such as Cilium and persistent network rules

3. **Run the playbook**:

   ```bash
   ansible-playbook create_install_manifest_files.yaml
   ```

  Ensure `ssh_public_key_<suffix>` is exported for the suffix configured in `openshift.install.bare_metal.ssh_public_key`.

4. **Run the Python module** to generate `server.json` and `nmstate_*.yaml` in `assisted-installer/`:

    ### Example: export sensitive variables and validate only

    ```bash
    cd openshift/install

    export redfish_password_1='replace-with-secret-1'
    export redfish_password_2='replace-with-secret-2'
    export fi_password_1='replace-with-fi-secret-1'
    export fi_password_2='replace-with-fi-secret-2'
    export ssh_public_key_1='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... your-user@example.com'

    # Optional: helps avoid GitHub API rate-limit issues when downloading release metadata/assets
    export GITHUB_TOKEN='replace-with-github-token'

    python generate_server_and_nmstate_templates.py --check-env
    ```

    ### Example: export sensitive variables and generate output

    ```bash
    cd openshift/install

    export redfish_password_1='replace-with-secret-1'
    export redfish_password_2='replace-with-secret-2'
    export fi_password_1='replace-with-fi-secret-1'
    export fi_password_2='replace-with-fi-secret-2'
    export ssh_public_key_1='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... your-user@example.com'
    export GITHUB_TOKEN='replace-with-github-token'  # optional

    python generate_server_and_nmstate_templates.py
    ```

5. **Prepare the iServer environment**, following:  **🔗 [iServer Console Setup](https://github.com/datacenter/iserver/blob/main/doc/ocp/Console.md)**

6. **Run iServer from the `assisted-installer/` directory**.

    First, check the data:

    ```bash
    cd assisted-installer
    ./iserver create ocp cluster bm --dir ./ --mode check
    ```

    Then run:

    ```bash
    ./iserver create ocp cluster bm --dir ./ --mode install
    ```

[Back to Table of Contents](#table-of-contents)

---

## Re-running the Playbook

This playbook is safe to re-run after variable changes. Existing generated files are overwritten with current desired values.

When rerunning, confirm any required sensitive environment variables are still exported in your current shell.

[Back to Table of Contents](#table-of-contents)

---

## Variables Reference

All variables live under the top-level `openshift:` key in your variables file. The table below describes the most important fields.

### `openshift.install.bare_metal`

| Key | Required | Description |
|-----|----------|-------------|
| `cluster_name` | Yes | Short name of the cluster (e.g. `ai-pods`) |
| `base_dns_domain` | Yes | Base DNS domain (e.g. `example.com`) |
| `cluster_version` | Yes | OpenShift version to install (e.g. `4.20.16`) |
| `cluster_networking.api.v4` | Yes (multi-node) | API VIP address |
| `cluster_networking.ingress.v4` | Yes (multi-node) | Ingress VIP address |
| `cluster_networking.cluster_network.v4_cidr` | Yes | Pod network CIDR |
| `cluster_networking.cluster_network.v4_host_prefix` | Yes | Per-node subnet prefix length |
| `cluster_networking.service_network.v4_cidr` | Yes | Service network CIDR |
| `cluster_networking.machine_network_gateway.v4` | Yes | Node network gateway in CIDR notation |
| `cluster_networking.dns_servers` | Yes | List of DNS server IPs |
| `cluster_networking.container_network_interface` | No | CNI plugin (`OVNKubernetes` or `Cilium`); defaults to `OVNKubernetes` |
| `ntp_servers` | No | List of NTP server addresses |
| `ssh_public_key` | Yes | Sensitive variable suffix for the SSH public key. For example, `ssh_public_key: 1` resolves `ssh_public_key_1` from the environment and writes it to `assisted-installer/ssh.pub`. |
| `fabric_interconnects` | Conditional | List of iServer Fabric Interconnect entries (required when any `servers[]` entry uses `fabric_interconnect`) |
| `iso_web_server` | Yes | ISO web server configuration (see below) |
| `servers` | Yes | List of cluster node definitions (see below) |
| `proxy` | No | HTTP/HTTPS proxy settings (see below) |

### `fabric_interconnects[]`

| Key | Description |
|-----|-------------|
| `ip` | Management IP of the Fabric Interconnect |
| `inventory_id` | iServer inventory identifier |
| `username` / `password` | iServer credentials (use Ansible Vault for passwords) |

### `iso_web_server`

| Key | Description |
|-----|-------------|
| `ip` | IP or hostname of the web server |
| `image_base_url` | Base URL used by iServer to download ISOs |
| `image_upload_directory` | Local path on the web server to upload ISOs |
| `username` | (Optional) Username for SSH-based upload |
| `ssh_public_key` | (Optional) Sensitive variable suffix for SSH public key based authentication. For example, `ssh_public_key: 1` resolves `ssh_public_key_1` from the environment. |
| `password` | (Optional) Environment variable suffix for password lookup |

### `servers[]`

Each entry describes one cluster node:

| Key | Description |
|-----|-------------|
| `hostname` | Node hostname |
| `role` | `master` or `worker` |
| `fabric_interconnect.id` | Index into the `fabric_interconnects` list |
| `fabric_interconnect.inventory_id` | iServer inventory ID for this node |
| `redfish.ip` / `.username` / `.password` / `.type` | Redfish BMC settings (alternative to FI-based boot). `password` is an environment variable suffix, not a plain-text secret. |
| `interfaces.ethernet[]` | Ethernet interface definitions (name, MAC, IPv4, MTU, LLDP) |
| `interfaces.bond[]` | Bond interface definitions |

### `openshift.operators`

| Key | Description |
|-----|-------------|
| `cilium.cluster_network.v4_cidr` | Pod CIDR to configure in CiliumConfig |
| `cilium.cluster_network.v4_host_prefix` | Per-node prefix size for Cilium IPAM |
| `cilium.enable_kube_proxy_replacement` | Enable full kube-proxy replacement in Cilium |
| `cilium.enable_hubble_metrics` | Enable extended Hubble flow metrics |
| `cilium.download_url` | URL to the Cilium/Clife operator tarball |
| `nvidia_network_operator.persistent_net_rules` | Per-host interface-to-MAC mappings for udev renaming |
| `portworx.enabled` | Generate Portworx multipathd MachineConfig manifests |

### `proxy` (optional)

| Key | Description |
|-----|-------------|
| `http_proxy` | HTTP proxy URL |
| `https_proxy` | HTTPS proxy URL |
| `no_proxy` | Comma-separated no-proxy list |
| `username` | Proxy username (injected into the URL) |
| `password` | Environment variable suffix for proxy password lookup |

[Back to Table of Contents](#table-of-contents)

---

## Feature Flags

The playbook conditionally generates additional manifests based on the variables provided:

| Condition | Manifests generated |
|-----------|---------------------|
| `openshift.operators.cilium.download_url` is set | Downloads Cilium tarball, renders `ciliumconfig.yaml` |
| `cilium.enable_kube_proxy_replacement: true` | Also renders `subscription.yaml` and `cluster-network-02-config-local.yaml` |
| `cilium.enable_hubble_metrics: true` | Enables extended Hubble metrics in `CiliumConfig` |
| `nvidia_network_operator.persistent_net_rules` is set | Renders `70-machine-config-udev-network.yaml` udev MachineConfig |
| `portworx.enabled: true` | Renders `99-portworx-multipathd-config-{master,worker}.yaml` |
| `openshift_install.proxy` is set | Renders `proxy.json` for iServer |

[Back to Table of Contents](#table-of-contents)

---

## Generated Output

After the playbook runs, the `assisted-installer/` directory will contain:

| File | Description |
|------|-------------|
| `cluster.json` | iServer cluster creation payload |
| `server.json` | Assisted Installer server inventory generated from `openshift.install.bare_metal.servers` |
| `nmstate_*.yaml` | Generated unique nmstate network profiles referenced by `server.json` |
| `ssh.pub` | SSH public key for node access |
| `web_server.json` | iServer ISO web server payload |
| `proxy.json` | iServer proxy payload (if proxy is configured) |
| `manifests/` | MachineConfig and operator manifests injected at install time |

When running `generate_server_and_nmstate_templates.py` (without `--check-env`), the script also downloads the latest Linux `.tar.gz` asset from [datacenter/iserver releases](https://github.com/datacenter/iserver/releases) and extracts it into `assisted-installer/`. If an iServer Linux `.tar.gz` archive already exists in `assisted-installer/`, the script reuses that local archive and skips downloading from GitHub.

[Back to Table of Contents](#table-of-contents)

---

## Troubleshooting

- `generate_server_and_nmstate_templates.py` fails with missing password env vars:
  - Run `python generate_server_and_nmstate_templates.py --check-env` to validate required environment variables.
  - Export all required `redfish_password_<suffix>`, `fi_password_<suffix>`, and `ssh_public_key_<suffix>` variables before generation.
- iServer tarball download fails:
  - Set `GITHUB_TOKEN` to avoid GitHub API rate limits.
  - Alternatively place a Linux iServer `.tar.gz` archive in `assisted-installer/` and rerun.
- Missing or incorrect `server.json`/`nmstate_*.yaml` output:
  - Re-check `openshift.install.bare_metal.servers` interface mappings and MAC addresses in the variables file.
  - Confirm each host has complete redfish or fabric interconnect details.
- iServer check/install mode fails:
  - Validate `cluster.json`, `web_server.json`, `ssh.pub`, `server.json`, and `nmstate_*.yaml` all exist under `assisted-installer/`.
  - Run check mode first: `./iserver create ocp cluster bm --dir ./ --mode check`.

[Back to Table of Contents](#table-of-contents)

---

## Acknowledgments

Special credit to GitHub user **akaliwod** for extensive work on the iServer project:

- [datacenter/iserver](https://github.com/datacenter/iserver)

[Back to Table of Contents](#table-of-contents)

---

## Security Notes

- **Never commit plain-text passwords.** Use [Ansible Vault](https://docs.ansible.com/ansible/latest/vault_guide/index.html) to encrypt sensitive values in your variables file.
- Proxy passwords and ISO web server passwords are resolved at runtime from environment variables (e.g., `export iso_web_server_password_<suffix>=...`), keeping credentials out of the YAML.
- SSH public keys are resolved at runtime from environment variables using this format: `ssh_public_key_<suffix>`.
- Redfish/BMC passwords are required at runtime via environment variables using this format: `redfish_password_<suffix>`.
- Fabric interconnect passwords are required at runtime via environment variables using this format: `fi_password_<suffix>`.
- The `<suffix>` comes from `openshift.install.bare_metal.ssh_public_key`, `servers[].redfish.password` for redfish hosts, or the resolved `fabric_interconnects[].password` value for FI-backed hosts.
- You can define as many suffixes as needed (for example: `ssh_public_key_1`, `redfish_password_1`, `redfish_password_2`, `fi_password_1`, `fi_password_17`, ...).
- Example: if `ssh_public_key: 1` in YAML, set `export ssh_public_key_1='ssh-ed25519 AAAAC...'` before running the generator.
- The generator validates that `ssh_public_key_<suffix>` is a real SSH public key before writing `assisted-installer/ssh.pub`.
- The nmstate/server generator exits with an error if a required `ssh_public_key_*`, `redfish_password_*`, or `fi_password_*` environment variable is missing.
- To validate only required credential env vars without generating files, run: `python generate_server_and_nmstate_templates.py --check-env`
- If GitHub API rate limits are encountered during release download, set `GITHUB_TOKEN` to increase API limits.
- The ISO web server template disables TLS verification when `https://` is detected in `image_base_url`. Use a trusted certificate in production environments.

[Back to Table of Contents](#table-of-contents)

