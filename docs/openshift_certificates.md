# Manage OpenShift Certificates (User CA, Ingress, API)

This folder contains Ansible playbooks to apply custom certificates to an OpenShift cluster in a controlled order:

1. Load a user CA bundle and patch cluster proxy trust.
2. Apply ingress wildcard certificate and key.
3. Apply API server named certificate and key.

It also includes validation playbooks for ingress and API certificate state.

**Back to OpenShift README:** [OpenShift Deployment Order](../README.md)

## Table of Contents

- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Certificate Requirements](#certificate-requirements)
- [Required Environment Variables](#required-environment-variables)
- [Playbook Features & Improvements](#playbook-features--improvements)
- [End-to-End Playbook](#end-to-end-playbook)
- [Validation Playbooks](#validation-playbooks)
- [Re-running the Playbook](#re-running-the-playbook)
- [Manual CSR Generation](#manual-csr-generation)
- [Manual Update Method](#manual-update-method)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Directory Structure

- load_certificates.yaml: Main end-to-end playbook (CA bundle, ingress cert, API cert)
- validate_ingress_certificate.yaml: Verifies ingress patch and restarts router/oauth pods
- validate_api_certificate.yaml: Waits until kube-apiserver rollout settles
- templates/user-ca-bundle.yaml.j2: ConfigMap template for user CA bundle
- templates/ingress-tls-secret.yaml.j2: Secret template for ingress TLS cert/key
- templates/api-tls-secret.yaml.j2: Secret template for API TLS cert/key
- backup/: Optional staging or backup files

[Back to Table of Contents](#table-of-contents)

## Prerequisites

- OpenShift CLI (`oc`) installed on the machine running Ansible
- Ansible collections:
  - kubernetes.core
  - community.crypto
- Cluster credentials with permission to patch cluster-scoped resources and create secrets/configmaps
- Certificate and key files available locally on the Ansible host

Install required collections:

```bash
ansible-galaxy collection install kubernetes.core community.crypto
```

[Back to Table of Contents](#table-of-contents)

## Certificate Requirements

- Private keys must be unencrypted PEM files.
- Ingress certificate must cover `*.apps.<cluster-name>.<base-domain>`.
- API certificate must include the external API hostname (`api.<cluster-name>.<base-domain>`) in SAN.
- Certificate chain files should include leaf cert first, then intermediates, then root.
- User CA bundle should contain trusted root CA(s) used by your org trust chain.

[Back to Table of Contents](#table-of-contents)

## Required Environment Variables

The playbooks read values from environment variables.

```bash
export openshift_api_url="https://api.<cluster>.<domain>:6443"
export openshift_token_id="<token>"

export user_ca_bundle_file="/path/to/user-ca-bundle.crt"

export ingress_cert_chain_file="/path/to/ingress.fullchain.crt"
export ingress_key_file="/path/to/ingress.key"

export api_cert_chain_file="/path/to/api.fullchain.crt"
export api_key_file="/path/to/api.key"
export api_server_hostname="api.<cluster>.<domain>"
```

Notes:

- `user_ca_bundle_file` is used to build ConfigMap `user-ca-bundle` in `openshift-config`.
- `ingress_*` values are used to create Secret `ingress-tls-secret` in `openshift-ingress`.
- `api_*` values are used to create Secret `api-tls-secret` in `openshift-config` and patch `apiserver/cluster`.

[Back to Table of Contents](#table-of-contents)

## Playbook Features & Improvements

The certificate playbooks include these reliability updates:

- Pre-task checks for `oc` CLI availability
- Required environment variable assertions before execution
- Certificate/key file existence checks before parsing
- Retry logic for login and Kubernetes apply operations
- Idempotent patching using `kubernetes.core.k8s` definitions for Proxy, IngressController, and APIServer resources
- Validation playbooks updated with the same preflight checks and login retry behavior

These improvements make certificate workflows safer to execute repeatedly and easier to troubleshoot.

[Back to Table of Contents](#table-of-contents)

## End-to-End Playbook

Run the full workflow:

```bash
ansible-playbook load_certificates.yaml
```

What it does:

1. Validates `user_ca_bundle_file` format using `community.crypto.x509_certificate_info`.
2. Logs into the cluster using token and API URL.
3. Creates/updates `user-ca-bundle` ConfigMap.
4. Patches `proxy/cluster` to trust `user-ca-bundle`.
5. Waits for master MCP update completion.
6. Prompts before ingress update.
7. Validates ingress cert/key file formats.
8. Creates/updates ingress TLS secret and patches default ingress controller.
9. Waits for OAuth and router pods to be ready.
10. Prompts before API update.
11. Validates API cert/key file formats.
12. Creates/updates API TLS secret and patches `apiserver/cluster` named certificate.
13. Waits for kube-apiserver rollout stabilization.

The playbook is intentionally phased with pause prompts before ingress and API changes.

[Back to Table of Contents](#table-of-contents)

## Validation Playbooks

Validate ingress certificate state and restart relevant pods:

```bash
ansible-playbook validate_ingress_certificate.yaml
```

Validate API certificate rollout state:

```bash
ansible-playbook validate_api_certificate.yaml
```

[Back to Table of Contents](#table-of-contents)

## Re-running the Playbook

The end-to-end certificate workflow is safe to re-run. Existing ConfigMaps, Secrets, and patched cluster resources are reconciled to the desired state.

If a run stops at a prompt or fails during rollout, fix the issue and run again:

```bash
ansible-playbook load_certificates.yaml
```

[Back to Table of Contents](#table-of-contents)

## Manual CSR Generation

### API CSR

Create `api.conf`:

```ini
[req]
default_bits = 2048
prompt = no
default_md = sha512
req_extensions = v3_req
distinguished_name = req_distinguished_name

[req_distinguished_name]
C = US
ST = California
L = San Jose
O = Example Company
OU = AI Admins
CN = api.<cluster-name>.<base-domain>
emailAddress = admins@example.com

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = api.<cluster-name>.<base-domain>
IP.1 = <api-vip>
```

Generate key and CSR:

```bash
openssl req -newkey rsa:2048 -keyout api-<cluster-name>.key -out api-<cluster-name>.csr -config api.conf -nodes
```

### Ingress CSR

Create `ingress.conf`:

```ini
[req]
default_bits = 2048
prompt = no
default_md = sha512
req_extensions = v3_req
distinguished_name = req_distinguished_name

[req_distinguished_name]
C = US
ST = California
L = San Jose
O = Example Company
OU = AI Admins
CN = apps.<cluster-name>.<base-domain>
emailAddress = admins@example.com

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = apps.<cluster-name>.<base-domain>
DNS.2 = *.apps.<cluster-name>.<base-domain>
IP.1 = <ingress-vip>
```

Generate key and CSR:

```bash
openssl req -newkey rsa:2048 -keyout apps-<cluster-name>.key -out apps-<cluster-name>.csr -config ingress.conf -nodes
```

[Back to Table of Contents](#table-of-contents)

## Manual Update Method

### 1. User CA Bundle

```bash
oc create configmap user-ca-bundle --from-file=ca-bundle.crt=<path-to-user-ca-bundle> -n openshift-config
oc patch proxy/cluster --type=merge --patch='{"spec":{"trustedCA":{"name":"user-ca-bundle"}}}'
```

### 2. Ingress Certificate

```bash
oc create secret tls ingress-tls-secret \
  --cert=<path-to-ingress-fullchain.crt> \
  --key=<path-to-ingress.key> \
  -n openshift-ingress

oc patch ingresscontroller.operator/default --type=merge \
  -p '{"spec":{"defaultCertificate":{"name":"ingress-tls-secret"}}}' \
  -n openshift-ingress-operator
```

### 3. API Certificate

```bash
oc create secret tls api-tls-secret \
  --cert=<path-to-api-fullchain.crt> \
  --key=<path-to-api.key> \
  -n openshift-config

oc patch apiserver cluster --type=merge -p '{"spec":{"servingCerts":{"namedCertificates":[{"names":["api.<cluster>.<domain>"],"servingCertificate":{"name":"api-tls-secret"}}]}}}'
```

Important:

- Do not configure a named cert for `api-int.<cluster>.<domain>`.
- Monitor operator rollout before declaring success.

[Back to Table of Contents](#table-of-contents)

## Troubleshooting

- PEM parsing failure:
  - Confirm files are PEM encoded and contain complete `BEGIN/END` blocks.
- Ingress still serving old cert:
  - Run `ansible-playbook validate_ingress_certificate.yaml` to restart router/oauth pods and wait for readiness.
- API not stabilized yet:
  - Run `ansible-playbook validate_api_certificate.yaml` and watch kube-apiserver conditions.
- Verify applied resources:

```bash
oc get configmap user-ca-bundle -n openshift-config -o yaml
oc get secret ingress-tls-secret -n openshift-ingress
oc get secret api-tls-secret -n openshift-config
oc get ingresscontroller.operator/default -n openshift-ingress-operator -o yaml
oc get apiserver cluster -o yaml
oc get clusteroperators kube-apiserver
```

[Back to Table of Contents](#table-of-contents)

## References

- [OpenShift Container Platform Documentation (docs.redhat.com)](https://docs.redhat.com/en/documentation/openshift_container_platform)
- [OpenShift Container Platform Documentation (access.redhat.com)](https://access.redhat.com/documentation/en-us/openshift_container_platform)
- [Custom Root CA in OpenShift (kenmoini.com)](https://kenmoini.com/post/2022/02/custom-root-ca-in-openshift/)

[Back to Table of Contents](#table-of-contents)
