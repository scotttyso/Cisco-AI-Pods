# Portworx Deployment with Everpure

This guide covers the Portworx-specific flow in this folder:

1. Generate `pure.json` credentials using Everpure APIs.
2. Install Portworx Operator and StorageCluster on OpenShift.
3. Create Portworx storage classes from template values.

**Back to OpenShift Deployment Order:** [OpenShift Deployment Order](openshift.md)

## Table of Contents

- [Portworx Deployment with Everpure](#portworx-deployment-with-everpure)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Configuration Inputs](#configuration-inputs)
  - [Step 1: Create pure.json](#step-1-create-purejson)
  - [Step 2: Install Portworx](#step-2-install-portworx)
  - [Step 3: Validate Portworx and Storage Classes](#step-3-validate-portworx-and-storage-classes)
  - [Step 4: Test PVC Provisioning](#step-4-test-pvc-provisioning)
  - [Troubleshooting](#troubleshooting)

## Prerequisites

- Ansible collections installed from the repository root `requirements.yaml` (see [Prepare the Environment](guide_prepare_the_environment.md#install-ansible-on-ubuntu))
- Python dependencies installed from the repository root `requirements.txt` (see [Prepare the Environment](guide_prepare_the_environment.md#install-ansible-on-ubuntu))
- OpenShift cluster access (`oc`) with sufficient privileges
- Everpure API tokens for every array/blade listed in variables

Install dependencies:

```bash
ansible-galaxy collection install -r requirements.yaml
pip install -r requirements.txt
```

[Back to Table of Contents](#table-of-contents)

## Configuration Inputs

Primary variable input:

- `host_vars/everpure/*.yaml`

> **Tip:** Edit `host_vars/everpure/everpure.ezai.yaml` with your environment values.

Important keys:

- `everpure.flash_arrays[]` and `everpure.flash_blades[]`
- `everpure.portworx.namespace`
- `everpure.portworx.cluster_name`
- `everpure.portworx.operator_source`
- `everpure.portworx.storage_classes[]`
- `everpure.portworx.version`

Environment variables used by playbooks:

```bash
# One token per api_token_id used in vars file
export pure_api_token_1="<flasharray_token>"
export pure_api_token_2="<flashblade_token>"

# OpenShift access (for Portworx deployment)
export openshift_api_url="https://api.<cluster>.<domain>:6443"
export openshift_token_id="<token>"
```

[Back to Table of Contents](#table-of-contents)

## Step 1-2: Create pure.json and Install Portworx

Generate Portworx credentials and install operator/storage (optional):

```bash
ansible-playbook playbooks/deploy_ai_pod.yaml --tags everpure,portworx
```

What this does:

- Creates/rotates a Portworx API user (`everpure.portworx.array_user`) on each FlashArray and FlashBlade.
- Collects generated API tokens.
- Renders `pure.json` from `templates/pure.json.j2`.
- Writes `pure.json` with restricted file permissions.

Expected output:

- `pure.json` file in this folder

[Back to Table of Contents](#table-of-contents)

Run the full Cisco AI Pods workflow instead:

```bash
ansible-playbook playbooks/deploy_ai_pod.yaml
```

What the Portworx role does:

1. Loads and validates required Portworx variables.
2. Validates required OpenShift environment variables.
3. Verifies `oc` availability and `pure.json` presence.
4. Logs in to OpenShift.
5. Creates namespace from `everpure.portworx.namespace`.
6. Creates or updates secret `px-pure-secret` from local `pure.json`.
7. Creates Portworx subscription `portworx-certified` in `openshift-operators`.
8. Waits for deployment `portworx-operator` to become ready.
9. Applies StorageCluster manifest.
10. Applies one StorageClass per entry in `everpure.portworx.storage_classes`.

[Back to Table of Contents](#table-of-contents)

## Step 3: Validate Portworx and Storage Classes

```bash
oc get pods -n openshift-operators | grep portworx
oc get pods -n <portworx-namespace>
oc get storagecluster -n <portworx-namespace>
oc get storageclass
```

Replace `<portworx-namespace>` with the value in `everpure.portworx.namespace` (default example is `portworx`).

[Back to Table of Contents](#table-of-contents)

## Step 4: Test PVC Provisioning

Example manifests are in `roles/portworx_csi/templates/`.

```bash
cd examples
oc apply -f pvc/
oc get pvc -A
```

Confirm PVCs bind successfully and backing volumes are created.

[Back to Table of Contents](#table-of-contents)

## Troubleshooting

- `pure.json` not generated:
  - Ensure every `api_token_id` in variables has a matching `pure_api_token_<id>` environment variable.
- Portworx operator not ready:
  - Check subscription and CSV in `openshift-operators`.
- Secret exists but contains old values:
  - Re-run `ansible-playbook playbooks/deploy_ai_pod.yaml --tags portworx` to reconcile `px-pure-secret`.
- StorageCluster not progressing:
  - Check events and describe the StorageCluster resource.

Helpful commands:

```bash
oc get subscription -n openshift-operators | grep portworx
oc get csv -n openshift-operators | grep -i portworx
oc describe storagecluster -n <portworx-namespace>
oc get events -n <portworx-namespace> --sort-by=.metadata.creationTimestamp
```

[Back to Table of Contents](#table-of-contents)
