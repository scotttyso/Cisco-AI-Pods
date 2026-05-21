# OpenShift Deployment Order

Use this guide to run the OpenShift workflow in the correct sequence.

## Table of Contents

- [OpenShift Deployment Order](#openshift-deployment-order)
  - [Table of Contents](#table-of-contents)
  - [Variable Files](#variable-files)
  - [Run Order](#run-order)
  - [Troubleshooting](#troubleshooting)

## Variable Files

- The [examples](examples) folder contains example variable files for each OpenShift module.
- Create the [script_vars](script_vars) folder if it does not exist:

  ```bash
  mkdir -p script_vars
  ```

- Copy the files you need from [examples](examples) into [script_vars](script_vars), then edit the copies with values for your environment.
- The module playbooks in the Run Order section below read their active inputs from [script_vars](script_vars).

Top-level project README:
- [Cisco-AI-Pods README](../README.md)

[Back to Table of Contents](#table-of-contents)

## Run Order

1. Install
- Generates base Assisted Installer payloads (`cluster.json`, `web_server.json`, `ssh.pub`) and, via the Python module, creates `server.json` plus `nmstate_*.yaml` profiles used for host networking and inventory mapping to be consumed with `iserver` module.
- [install README](openshift_install.md)

2. Certificates
- Applies trust bundle, ingress wildcard certificate, and API server certificate updates, then validates certificate rollout/state on the cluster.
- [certificates README](openshift_certificates.md)

3. Everpure Portworx Install
- Prepares Everpure credentials, installs Portworx Operator/StorageCluster, and creates StorageClasses for persistent workload storage.
- [Everpure Portworx README](../portworx.md)

4. OATH LDAP (Optional for Active Directory Authentication)
- Configures OpenShift OAuth/LDAP integration for AD sign-in and deploys group sync resources (including scheduled synchronization).
- [oath_ldap README](openshift_auth.md)

5. Base Operators
- Installs foundational operators needed before higher-level platform automation.
- [base_operators README](base_operators/README.md)
- Note: Gitea is only required if another Git service is not available.
- [base_operators/gitea README](openshift_argo_cd.md)

6. OpenShift GitOps
- Generates and stages GitOps repository content (Helm/OLM trees and rendered Argo CD applications) consumed by OpenShift GitOps.
- [openshift-gitops README](openshift_gitops.md)

[Back to Table of Contents](#table-of-contents)

## Troubleshooting

- Workflow fails during install manifest generation:
  - Validate required environment variables for redfish/FI passwords are exported before running the install workflow.
  - See [install README](openshift_install.md).
- Certificate rollout is incomplete:
  - Verify certificate resources were applied and ingress/API pods were restarted as expected.
  - See [certificates README](openshift_certificates.md).
- LDAP users cannot authenticate:
  - Confirm bind credentials and LDAP sync objects are correct and sync jobs complete successfully.
  - See [oath_ldap README](openshift_auth.md).
- GitOps applications fail to sync:
  - Verify generated manifests are present in the target repository path and operator CRDs are installed first.
  - See [openshift-gitops README](openshift_gitops.md).

[Back to Table of Contents](#table-of-contents)

Back to top-level:
- [Cisco-AI-Pods README](../README.md)
