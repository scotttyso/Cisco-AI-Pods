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

- Array deployment guide: [everpure_arrays.md](everpure_arrays.md)
- Portworx deployment guide: [everpure_portworx.md](everpure_portworx.md)

[Back to Table of Contents](#table-of-contents)

## Folder Contents

- `playbooks/deploy_ai_pod.yaml`: Full-stack entry point playbook (includes Everpure and Portworx roles)
- `host_vars/everpure/`: Active Everpure configuration variables
- `roles/everpure/tasks/`: Everpure task files for FlashArray and FlashBlade workflows
- `roles/everpure/templates/`: Templates for `pure.json`, StorageCluster, and storage classes
- `roles/portworx_csi/tasks/`: Portworx task files for operator and StorageCluster deployment

[Back to Table of Contents](#table-of-contents)

## Prerequisites

Install required Ansible collections from the repository root requirements file by following:

- [Prepare the Environment](guide_prepare_the_environment.md#install-ansible-on-ubuntu)

Example:

```bash
ansible-galaxy collection install -r requirements.yaml
```

Install required Python dependencies:

```bash
pip install -r requirements.txt
```

[Back to Table of Contents](#table-of-contents)

## Deployment Order

Use this order to avoid dependency issues:

1. Configure Everpure arrays (FlashArray/FlashBlade) if needed.
2. Generate `pure.json` for Portworx authentication.
	Note: Complete the OpenShift installation workflow in [openshift.md](openshift.md) before starting the Portworx installation and StorageCluster tasks.
3. Install Portworx and StorageCluster on OpenShift.

Detailed procedures are documented in:

- [everpure_arrays.md](everpure_arrays.md)
- [everpure_portworx.md](everpure_portworx.md)

[Back to Table of Contents](#table-of-contents)

## Quick Start

1. Edit your active Everpure YAML in `host_vars/everpure/`.
2. Export the required Everpure API tokens.
3. Run Everpure and Portworx (optional):

```bash
ansible-playbook playbooks/deploy_ai_pod.yaml --tags everpure,portworx
```

Run the full Cisco AI Pods workflow (all domains) instead:

```bash
ansible-playbook playbooks/deploy_ai_pod.yaml
```

[Back to Table of Contents](#table-of-contents)

## Environment Variables

Common variables used in this folder:

```bash
# Everpure API tokens (match api_token_id values in host_vars/everpure/)
export pure_api_token_1="<flasharray_token>"
export pure_api_token_2="<flashblade_token>"

# OpenShift access for Portworx deployment
export openshift_api_url="https://api.<cluster>.<domain>:6443"
export openshift_token_id="<token>"
```

Note: Additional sensitive variables may be required depending on your array security settings in your `host_vars/everpure/` YAML.

[Back to Table of Contents](#table-of-contents)
