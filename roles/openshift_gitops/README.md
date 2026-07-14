# OpenShift GitOps Role

Generates GitOps repository content (Helm charts and OLM operator manifests) consumed by OpenShift GitOps (Argo CD).

**Main Documentation:** [docs/openshift.md — GitOps](../../docs/openshift.md#gitops)

## Role Tasks

- `main.yaml` — Loads merged variables, copies Helm/OLM trees, renders Argo CD Application manifests

## What It Does

1. Loads merged YAML from `host_vars/openshift/*.ezai.yaml`
2. Creates destination directory if missing
3. Copies `roles/openshift_gitops/helm/` to destination
4. Copies `roles/openshift_gitops/olm_catalog/` to destination
5. Renders `lldp-daemonset.yaml` (always)
6. Renders one operator manifest per entry in `operators_to_install`
7. Renders Ansible Automation Platform extra resources (if selected)
8. Renders Mac VLAN policies per NVIDIA Network Operator config (if selected)

## Files

| File | Description |
|------|-------------|
| `tasks/main.yaml` | Role entry point for GitOps content generation |
| `defaults/main.yaml` | Role defaults (empty) |
| `helm/` | Helm charts copied to destination |
| `olm_catalog/` | OLM catalog/operator templates copied to destination |
| `templates/*.j2` | Jinja2 templates for Argo CD Applications |

## Key Variables

Set in `host_vars/openshift/operators.ezai.yaml`:

| Variable | Description |
|----------|-------------|
| `openshift.destination_directory` | Output path (default: `_generated_gitops`) |
| `openshift.base_dns_domain` | Cluster base DNS (default: `example.com`) |
| `openshift.cluster_name` | Cluster name (default: `default`) |
| `openshift.file_storage_class` | Storage class for AAP (if using AAP) |
| `openshift.operators.openshift_gitops.gitops_repo_url` | **Required** — GitOps repo URL |
| `openshift.operators.openshift_gitops.prune` | Auto-prune (default: `false`) |
| `openshift.operators.openshift_gitops.self_heal` | Auto-heal (default: `true`) |
| `openshift.operators.operators_to_install` | List of operators to render |
| `openshift.operators.nvidia_network_operator.mac_vlan` | Mac VLAN network policies |

## Available Operators

Include in `operators_to_install`:

- `ansible-automation-platform`
- `external-secrets-operator`
- `gpu-operator`
- `infrastructure-operators`
- `intersight-operator`
- `kubernetes-nmstate-operator`
- `node-feature-discovery-operator`
- `nvidia-gpu-operator`
- `nvidia-network-operator`
- `observability-operators`
- `openshift-virtualization`
- `rhoai-application`
- `scaling-operators`

Each must have a matching template: `templates/<name>.yaml.j2`

## Generated Output Structure

```
<destination>/
├── helm/                                          # Copied from role
│   ├── gpu-operator-installation/
│   ├── helm-operator-config/
│   └── ...
├── olm-catalog/                                   # Copied from role
│   ├── operators/
│   │   ├── lldp-daemonset.yaml                   # Always rendered
│   │   ├── gpu-operator.yaml                     # Per operators_to_install
│   │   ├── nvidia-network-operator.yaml
│   │   └── ...
│   ├── ansible-automation-platform/              # If AAP selected
│   │   ├── 04-ansible-automation-platform.yaml
│   │   └── 04-console-link-aap.yaml
│   └── ...
```

## Idempotency

Safe to re-run. Existing files are reconciled with current variable values.

## Validation

Check generated files:
```bash
find <destination>/olm-catalog/operators -maxdepth 1 -name '*.yaml' | sort

# Verify repo URLs are correct
grep -R "repoURL:" <destination>/olm-catalog

# Check Mac VLAN policies
grep -R "MacvlanNetwork" <destination>/helm
```

## Troubleshooting

- **gitops_repo_url is required:** Add to variables file
- **Operators not rendering:** Ensure every item in `operators_to_install` has matching template
- **Wrong destination:** Verify `openshift.destination_directory` path
- **AAP console link wrong domain:** Set `openshift.base_dns_domain` in variables
- **No Mac VLAN files:** Ensure `nvidia-network-operator` in operators list and mac_vlan entries defined

Check variables:
```bash
cd roles/openshift_gitops
python -c "import yaml; print(yaml.safe_load(open('../../host_vars/openshift/operators.ezai.yaml'))['openshift'])"
```

See [docs/openshift.md — GitOps](../../docs/openshift.md#gitops) for full setup guide.

## Important Notes

- LLDP DaemonSet always renders
- If deploying OpenTelemetry for observability, also deploy [Splunk Observability](../../docs/splunk_observability.md)
- Generated content should be committed to GitOps repo before Argo CD syncs it
