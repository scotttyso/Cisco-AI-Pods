# Install OpenShift GitOps Operator

This folder contains an Ansible playbook that installs the OpenShift GitOps Operator and related RBAC/operator resources.

**Back to Base Operators README:** [Base Operators Overview](../README.md)

## Table of Contents

- [Install OpenShift GitOps Operator](#install-openshift-gitops-operator)
  - [Table of Contents](#table-of-contents)
  - [Directory Structure](#directory-structure)
  - [What the Playbook Does](#what-the-playbook-does)
  - [Prerequisites](#prerequisites)
  - [Playbook Features \& Improvements](#playbook-features--improvements)
  - [Required Environment Variables](#required-environment-variables)
  - [How to Run](#how-to-run)
  - [Re-running the Playbook](#re-running-the-playbook)
  - [Validation](#validation)
  - [Troubleshooting](#troubleshooting)

## Directory Structure

- install_openshift_gitops.yaml: Main installation playbook
- templates/operator-group.yaml.j2: OperatorGroup manifest
- templates/rbac.yaml.j2: ClusterRoleBinding manifest for GitOps application controller
- templates/subscription.yaml.j2: Operator subscription manifest

[Back to Table of Contents](#table-of-contents)

## What the Playbook Does

The playbook currently performs these steps:

1. Logs in to OpenShift with token and API URL from environment variables.
2. Creates namespace openshift-gitops-operator.
3. Creates Subscription openshift-gitops-operator in openshift-gitops-operator.
4. Creates OperatorGroup in openshift-gitops-operator.
5. Creates ClusterRoleBinding openshift-gitops-cluster-admin.
6. Waits for Deployment openshift-gitops-operator-controller-manager to become available.

[Back to Table of Contents](#table-of-contents)

## Prerequisites

- OpenShift CLI (oc) installed on the host running Ansible
- Ansible with kubernetes.core collection installed
- Permissions to create namespaces, OLM resources, and cluster RBAC
- Access to Red Hat operator catalog source redhat-operators in openshift-marketplace

Install required collection:

```bash
ansible-galaxy collection install kubernetes.core
```

[Back to Table of Contents](#table-of-contents)

## Playbook Features & Improvements

The playbook includes these reliability updates:

- Pre-task validation for `oc` CLI availability
- Pre-task validation for required `openshift_api_url` and `openshift_token_id` environment variables
- Retry logic on login and Kubernetes apply tasks (3 attempts, 5-second delay)
- Idempotent resource management through `kubernetes.core.k8s` with `state: present`

These updates improve reliability and make repeated runs safe.

[Back to Table of Contents](#table-of-contents)

## Required Environment Variables

Export before running:

```bash
export openshift_api_url="https://api.<cluster>.<domain>:6443"
export openshift_token_id="<token>"
```

To get these in OpenShift web console:

- User menu (top-right)
- Copy login command
- Display Token

![Copy Login Command](images/openshift/copy_login_command.png)
![Display Token](images/openshift/display_token.png)

[Back to Table of Contents](#table-of-contents)

## How to Run

From this directory:

```bash
ansible-playbook install_openshift_gitops.yaml
```

[Back to Table of Contents](#table-of-contents)

## Re-running the Playbook

This playbook is safe to re-run and will reconcile existing resources.

If execution fails, resolve the root cause and run again:

```bash
ansible-playbook install_openshift_gitops.yaml
```

[Back to Table of Contents](#table-of-contents)

## Validation

Validate operator install:

```bash
oc get ns openshift-gitops-operator
oc get subscription -n openshift-gitops-operator
oc get csv -n openshift-gitops-operator
oc get deployment openshift-gitops-operator-controller-manager -n openshift-gitops-operator
oc get clusterrolebinding openshift-gitops-cluster-admin
```

[Back to Table of Contents](#table-of-contents)

## Troubleshooting

- Login failed:
  - Confirm openshift_api_url and openshift_token_id are exported in the same shell that runs ansible-playbook.
- Subscription/CSV does not progress:
  - Check events and catalog source availability in openshift-gitops-operator and openshift-marketplace.
- Deployment readiness timeout:
  - Describe deployment and check operator pod logs.

Helpful commands:

```bash
oc describe subscription openshift-gitops-operator -n openshift-gitops-operator
oc get csv -n openshift-gitops-operator
oc get events -n openshift-gitops-operator --sort-by=.metadata.creationTimestamp
oc logs deployment/openshift-gitops-operator-controller-manager -n openshift-gitops-operator
```

[Back to Table of Contents](#table-of-contents)
