# Cisco AI Pods Everpure Overview

This folder contains Everpure automation used by Cisco AI Pods for two main workflows:

- Everpure array configuration (FlashArray and FlashBlade)
- Portworx integration and deployment on OpenShift

## Table of Contents

- [Cisco AI Pods Everpure Overview](#cisco-ai-pods-everpure-overview)
  - [Table of Contents](#table-of-contents)
  - [Runbook Documents](#runbook-documents)
  - [Folder Contents](#folder-contents)
  - [Prerequisites](#prerequisites)
  - [Deployment Order](#deployment-order)
  - [Quick Start](#quick-start)
  - [Environment Variables](#environment-variables)

## Runbook Documents

- Array deployment guide: [README_everpure_arrays.md](README_everpure_arrays.md)
- Portworx deployment guide: [README_portworx.md](README_portworx.md)

[Back to Table of Contents](#table-of-contents)

## Folder Contents

- `configure_everpure_arrays.yaml`: Configures FlashArray and FlashBlade using values from `script_vars/*.yaml`
- `create_pure_json.yaml`: Creates `pure.json` used by the Portworx secret
- `install_portworx.yaml`: Installs Portworx operator and deploys StorageCluster/storage classes
- `pure.json`: Generated credentials payload for `px-pure-secret`
- `script_vars/`: Active configuration values loaded at runtime (`*.yaml`)
- `tasks/`: Task files for FlashArray, FlashBlade, and Portworx workflows
- `templates/`: Templates for `pure.json`, StorageCluster, and storage classes
- `examples/`: Example input YAML files — copy one to `script_vars/` as a starting point for your environment

[Back to Table of Contents](#table-of-contents)

## Prerequisites

Install required Ansible collections from the repository root requirements file by following:

- [Prepare the Environment](../guide_prepare_the_environment.md#install-ansible-on-ubuntu)

Example:

```bash
cd ..
ansible-galaxy collection install -r requirements.yaml
cd everpure
```

Install required Python dependencies:

```bash
cd ..
pip install -r requirements.txt
cd everpure
```

[Back to Table of Contents](#table-of-contents)

## Deployment Order

Use this order to avoid dependency issues:

1. Configure Everpure arrays (FlashArray/FlashBlade) if needed.
2. Generate `pure.json` for Portworx authentication.
	Note: Complete the OpenShift installation workflow in [../openshift/README.md](../openshift/README.md) before starting the Portworx installation and StorageCluster tasks.
3. Install Portworx and StorageCluster on OpenShift.

Detailed procedures are documented in:

- [README_everpure_arrays.md](README_everpure_arrays.md)
- [README_portworx.md](README_portworx.md)

[Back to Table of Contents](#table-of-contents)

## Quick Start

1. Place your active Everpure YAML in `script_vars/`.
2. Export the required Everpure API tokens.
3. Run the Everpure preparation playbooks:

```bash
ansible-playbook configure_everpure_arrays.yaml
ansible-playbook create_pure_json.yaml
```

4. Complete the OpenShift installation workflow described in [../openshift/README.md](../openshift/README.md).
5. Export the OpenShift credentials required by `install_portworx.yaml`.
6. Run the Portworx installation playbook:

```bash
ansible-playbook install_portworx.yaml
```

[Back to Table of Contents](#table-of-contents)

## Environment Variables

Common variables used in this folder:

```bash
# Everpure API tokens (match api_token_id values in script_vars)
export pure_api_token_1="<flasharray_token>"
export pure_api_token_2="<flashblade_token>"

# OpenShift access for install_portworx.yaml
export openshift_api_url="https://api.<cluster>.<domain>:6443"
export openshift_token_id="<token>"
```

Note: Additional sensitive variables may be required depending on your array security settings in your `script_vars` YAML.

[Back to Table of Contents](#table-of-contents)
