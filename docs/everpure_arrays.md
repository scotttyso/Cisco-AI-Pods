# Everpure Arrays Deployment Guide

This guide covers Day 0 automation for Everpure FlashArray and FlashBlade configuration in this folder.

## Table of Contents

- [Everpure Arrays Deployment Guide](#everpure-arrays-deployment-guide)
  - [Table of Contents](#table-of-contents)
  - [Scope](#scope)
  - [Prerequisites](#prerequisites)
  - [Configuration Files](#configuration-files)
  - [Environment Variables](#environment-variables)
  - [Run the Array Configuration Playbook](#run-the-array-configuration-playbook)
  - [What Gets Configured](#what-gets-configured)
  - [Verification](#verification)
  - [Troubleshooting](#troubleshooting)

## Scope

The array workflow configures settings on FlashArray and FlashBlade using task sets under:

- `tasks/flash_array/`
- `tasks/flash_blade/`

This includes network, security/access, system, users, and (for FlashBlade) optional notification integrations based on the values you provide.

[Back to Table of Contents](#table-of-contents)

## Prerequisites

- Ansible collections installed from the repository root `requirements.yaml` (see [Prepare the Environment](../guide_prepare_the_environment.md#install-ansible-on-ubuntu))
- Python dependencies installed from the repository root `requirements.txt` (see [Prepare the Environment](../guide_prepare_the_environment.md#install-ansible-on-ubuntu))
- Network connectivity from Ansible host to all array management endpoints
- API tokens for each array entry in your variables

Install dependencies:

```bash
cd ..
ansible-galaxy collection install -r requirements.yaml
pip install -r requirements.txt
cd everpure
```

[Back to Table of Contents](#table-of-contents)

## Configuration Files

Current files in this folder:

- `script_vars/*.yaml`: variable definitions loaded by the playbook
- `configure_everpure_arrays.yaml`: array configuration playbook

> **Tip:** The `examples/` folder contains a sample input YAML file. Copy it to `script_vars/` and update the values for your environment:
> ```bash
> cp examples/everpure.ezai.yaml script_vars/
> ```

The playbook validates that `everpure` exists and that at least one of `everpure.flash_arrays` or `everpure.flash_blades` is defined before running tasks.

[Back to Table of Contents](#table-of-contents)

## Environment Variables

Set one API token per `api_token_id` used in your variable file.

Example:

```bash
export pure_api_token_1="<flasharray_token>"
export pure_api_token_2="<flashblade_token>"
```

Additional environment variables may be required by your selected security/system options, for example bind or service account passwords referenced via lookups in task files.

[Back to Table of Contents](#table-of-contents)

## Run the Array Configuration Playbook

From this folder:

```bash
ansible-playbook configure_everpure_arrays.yaml
```

[Back to Table of Contents](#table-of-contents)

## What Gets Configured

Based on your variable content, the playbook iterates through:

- `everpure.flash_arrays[]`
- `everpure.flash_blades[]`

FlashArray tasks include:

- Settings: network
- Settings: access/security
- Settings: system

FlashBlade tasks include:

- Settings: network
- Settings: security
- Settings: system
- Notifications (if `everpure.notifications` is defined)

[Back to Table of Contents](#table-of-contents)

## Verification

Validate expected changes in Pure UI or via API/CLI checks.

Suggested checks:

```bash
# Example API version check
curl -k https://<array-management-endpoint>/api/api_version
```

```bash
# Re-run facts gathering in check mode style (optional pattern)
ansible localhost -m purestorage.flasharray.purefa_info -a "fa_url=<flasharray_fqdn> api_token=$pure_api_token_1 gather_subset=minimum" -c local
```

```bash
ansible localhost -m purestorage.flashblade.purefb_info -a "fb_url=<flashblade_fqdn> api_token=$pure_api_token_2" -c local
```

[Back to Table of Contents](#table-of-contents)

## Troubleshooting

- Authentication errors:
  - Confirm `pure_api_token_<id>` environment variable names match `api_token_id` values.
- Variable load failures:
  - Confirm at least one YAML file exists in `script_vars/` and contains a `everpure` root key.
- Module import errors:
  - Reinstall required collections and Python packages from the repository root `requirements.yaml` and `requirements.txt`.
  - See [Prepare the Environment](../guide_prepare_the_environment.md#install-ansible-on-ubuntu).
- Task skipped unexpectedly:
  - Check conditional keys like `everpure.settings.network`, `everpure.settings.security`, `everpure.settings.system`, and `everpure.notifications`.

[Back to Table of Contents](#table-of-contents)
