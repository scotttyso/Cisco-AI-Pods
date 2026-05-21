# OpenShift Argo CD Role

Installs the OpenShift GitOps Operator (Argo CD) on OpenShift clusters.

**Main Documentation:** [docs/openshift.md — Argo CD](../../docs/openshift.md#argo-cd)

## Role Tasks

- `main.yaml` — Validates prerequisites, installs GitOps Operator, sets up RBAC, verifies deployment

## What It Does

1. Validates `oc` CLI and required environment variables
2. Creates `openshift-gitops-operator` namespace
3. Creates OperatorGroup in namespace
4. Creates Subscription for OpenShift GitOps from `redhat-operators` catalog
5. Creates ClusterRoleBinding for `openshift-gitops-cluster-admin`
6. Waits for operator deployment (`openshift-gitops-operator-controller-manager`) to be ready

## Files

| File | Description |
|------|-------------|
| `tasks/main.yaml` | Role entry point with installation and validation |
| `defaults/main.yaml` | Role defaults |
| `templates/operator-group.yaml.j2` | OperatorGroup manifest |
| `templates/subscription.yaml.j2` | Operator subscription manifest |
| `templates/rbac.yaml.j2` | ClusterRoleBinding manifest |

## Key Variables

Set via environment variables:

- `openshift_api_url` — OpenShift API URL (e.g., `https://api.<cluster>.<domain>:6443`)
- `openshift_token_id` — OpenShift API token

No variables file needed — this role works with environment variables only.

## Idempotency

Fully idempotent. Safe to re-run. Resources are reconciled to desired state.

## Verification

Check installation status:
```bash
oc get ns openshift-gitops-operator
oc get operatorgroup -n openshift-gitops-operator
oc get subscription -n openshift-gitops-operator
oc get csv -n openshift-gitops-operator
oc get deployment -n openshift-gitops-operator
```

Access Argo CD:
```bash
# Get ArgoCD routes
oc get route -n openshift-gitops

# Get initial admin password
oc extract secret/openshift-gitops-creds -n openshift-gitops --to=- | grep admin.password
```

## Troubleshooting

- **Subscription not installing:** Check OperatorHub is available and `redhat-operators` catalog exists
- **CSV not reaching Succeeded:** Inspect logs: `oc logs -n openshift-gitops-operator deploy/openshift-gitops-operator-controller-manager`
- **Operator not becoming ready:** Check events: `oc describe deploy/openshift-gitops-operator-controller-manager -n openshift-gitops-operator`
- **Token expired:** Get fresh token from OpenShift web console
- **API unreachable:** Verify cluster endpoint and network connectivity

Check all resources:
```bash
oc get all -n openshift-gitops-operator
oc get csv -n openshift-gitops-operator -o yaml
oc describe subscription openshift-gitops-operator -n openshift-gitops-operator
```

## Dependencies

This role depends on:
- `kubernetes.core` Ansible collection

Install prerequisites:
```bash
ansible-galaxy collection install kubernetes.core
```

See [docs/openshift.md — Argo CD](../../docs/openshift.md#argo-cd) for full setup guide.
