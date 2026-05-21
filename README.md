# Cisco AI Pods Repository Guide

This repository contains automation and runbooks for Cisco AI Pods infrastructure across Intersight, storage, OpenShift, and observability workflows.

## Table of Contents

- [Cisco AI Pods Repository Guide](#cisco-ai-pods-repository-guide)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Primary Workstreams](#primary-workstreams)
  - [Repository Layout](#repository-layout)
  - [Runbook Documents](#runbook-documents)
  - [Environment Preparation](#environment-preparation)
  - [Quick Start Workflow](#quick-start-workflow)
  - [Common Commands](#common-commands)
  - [Troubleshooting and Operations](#troubleshooting-and-operations)
  - [Architecture](#architecture)
  - [Support and Contribution](#support-and-contribution)

## Overview

The repository provides centralized Ansible-based automation for complete Cisco AI Pods infrastructure deployment across:

- **Intersight and UCS** - Policy provisioning, resource pool management, and server profile deployment
- **Everpure Storage** - FlashArray and FlashBlade configuration with Portworx CSI integration
- **Red Hat OpenShift** - Cluster installation, authentication, certificates, GitOps, and ArgoCD
- **Splunk Observability** - Full-stack visibility and monitoring integration

All workflows use centralized playbooks in `playbooks/` with tag-based conditional execution and variable auto-loading from `host_vars/`.

## Primary Workstreams

All workflows execute through centralized Ansible playbooks from the repository root:

1. **Full Stack Deployment** (`playbooks/deploy_ai_pod.yml`)
   - Orchestrates all domains in deployment order
   - Automatically loads variables from `host_vars/` subdirectories
   - Supports `--tags` for selective execution

2. **Intersight and UCS** (`playbooks/deploy_ai_pod.yml --tags intersight`)
   - Guide: [docs/intersight.md](docs/intersight.md)
   - Includes policy, pool, and profile provisioning

3. **Everpure Storage and Portworx** (`playbooks/deploy_ai_pod.yml --tags everpure,portworx`)
   - Guide: [docs/everpure.md](docs/everpure.md)
   - Array configuration: [docs/everpure_arrays.md](docs/everpure_arrays.md)
   - Portworx CSI: [docs/everpure_portworx.md](docs/everpure_portworx.md)

4. **OpenShift Platform** (`playbooks/deploy_openshift.yml` or `playbooks/deploy_ai_pod.yml --tags openshift`)
   - Guide: [docs/openshift.md](docs/openshift.md)
   - Includes authentication, certificates, GitOps, and ArgoCD

5. **Splunk Observability** (`playbooks/deploy_ai_pod.yml --tags observability`)
   - Guide: [docs/splunk_observability.md](docs/splunk_observability.md)
   - Full-stack monitoring and observability integration

## Repository Layout

Top-level structure:

```text
Cisco-AI-Pods/
  docs/                          # All documentation
    intersight.md
    openshift.md
    everpure.md
    splunk_observability.md
    guide_cisco_ai_pods_runbook.md
    guide_prepare_the_environment.md
    guide_troubleshooting.md
  playbooks/                     # Centralized Ansible playbooks
    deploy_ai_pod.yml            # Full stack orchestration
    deploy_openshift.yml         # OpenShift only
    deploy_storage.yml           # Storage/Portworx only
    deploy_intersight_ucs.yml    # Intersight only
    deploy_observability.yml     # Splunk Observability only
  roles/                         # Ansible roles
    intersight_*/
    openshift_*/
    everpure/
    portworx_csi/
    splunk_observability/
  host_vars/                     # Environment variables (auto-loaded)
    everpure/
    intersight/
    openshift/
    splunk_observability/
  examples/                      # Example variable templates
  schema/                        # YAML schema for validation
  requirements.txt               # Python dependencies
  requirements.yaml              # Ansible collection dependencies
```

## Runbook Documents

All documentation is in the `docs/` folder:

- **Start here:** [docs/guide_prepare_the_environment.md](docs/guide_prepare_the_environment.md) — Install dependencies and prepare your environment
- **Main runbook:** [docs/guide_cisco_ai_pods_runbook.md](docs/guide_cisco_ai_pods_runbook.md) — Complete deployment workflow and playbook usage
- **Troubleshooting:** [docs/guide_troubleshooting.md](docs/guide_troubleshooting.md) — Cross-component triage and solutions
- **Domain-specific guides:**
  - [docs/intersight.md](docs/intersight.md) — Intersight/UCS provisioning
  - [docs/openshift.md](docs/openshift.md) — OpenShift deployment
  - [docs/everpure.md](docs/everpure.md) — Storage configuration
  - [docs/splunk_observability.md](docs/splunk_observability.md) — Observability integration

## Environment Preparation

Prepare tools and dependencies first:

1. Follow [docs/guide_prepare_the_environment.md](docs/guide_prepare_the_environment.md).
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Ansible collections:
   ```bash
   ansible-galaxy collection install -r requirements.yaml
   ```

## Quick Start Workflow

### 1. Prepare Environment

```bash
# Install dependencies
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yaml

# Copy example variables to host_vars/ and customize for your environment
mkdir -p host_vars
cp -r examples/intersight host_vars/
cp -r examples/openshift host_vars/
cp -r examples/everpure host_vars/
cp -r examples/splunk_observability host_vars/
```

### 2. Deploy Full Stack (All Domains)

```bash
ansible-playbook playbooks/deploy_ai_pod.yml
```

### 3. Deploy Specific Domains (Optional)

**Intersight and UCS only:**
```bash
ansible-playbook playbooks/deploy_ai_pod.yml --tags intersight
```

**Storage and Portworx only:**
```bash
ansible-playbook playbooks/deploy_ai_pod.yml --tags everpure,portworx
```

**OpenShift only:**
```bash
ansible-playbook playbooks/deploy_openshift.yml
```

**Splunk Observability only:**
```bash
ansible-playbook playbooks/deploy_ai_pod.yml --tags observability
```

For detailed procedures, see [docs/guide_cisco_ai_pods_runbook.md](docs/guide_cisco_ai_pods_runbook.md).

## Common Commands

Run playbook in dry-run mode (check mode):

```bash
ansible-playbook playbooks/deploy_ai_pod.yml --check
```

Run with verbose output for debugging:

```bash
ansible-playbook playbooks/deploy_ai_pod.yml -vvv
```

List all available tags:

```bash
ansible-playbook playbooks/deploy_ai_pod.yml --list-tags
```

Run a specific role or tag:

```bash
ansible-playbook playbooks/deploy_ai_pod.yml --tags certificates
```

## Troubleshooting and Operations

- **Cross-component triage:** [docs/guide_troubleshooting.md](docs/guide_troubleshooting.md)
- **Domain-specific issues:**
  - Intersight: [docs/intersight.md](docs/intersight.md)
  - OpenShift: [docs/openshift.md](docs/openshift.md)
  - Storage: [docs/everpure.md](docs/everpure.md)
  - Observability: [docs/splunk_observability.md](docs/splunk_observability.md)
- Keep `host_vars/` configurations and documentation synchronized as environments evolve
- Variables are auto-loaded from `host_vars/` subdirectories at runtime — no manual file copying needed

## Architecture

The repository uses a centralized Ansible architecture:

- **Playbooks** (`playbooks/deploy_*.yml`) — Orchestrate roles in dependency order
- **Roles** (`roles/*/`) — Task implementations for each domain
- **Variables** (`host_vars/<domain>/`) — Environment-specific configuration auto-loaded at runtime
- **Tags** — Control which roles execute via `--tags` flag
- **Examples** (`examples/`) — Template variable files for reference
- **Schema** (`schema/`) — YAML validation for configuration files

For detailed architecture information, see [docs/guide_cisco_ai_pods_runbook.md](docs/guide_cisco_ai_pods_runbook.md).

## Support and Contribution

For issues, feature requests, or contributions, please use the GitHub repository issue tracker.

For detailed deployment procedures, consult the documentation in `docs/`.