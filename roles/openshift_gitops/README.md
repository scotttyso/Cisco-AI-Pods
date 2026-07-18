# OpenShift GitOps Role

Generates GitOps repository content (Helm charts and OLM operator manifests) consumed by OpenShift GitOps (Argo CD).

**Main Documentation:** [docs/openshift.md — GitOps](../../docs/openshift.md#gitops)

## Role Tasks

- `main.yaml` — Loads merged variables, copies Helm/OLM trees, renders Argo CD Application manifests

## What It Does

1. Loads merged YAML from `host_vars/openshift/*.ezai.yaml`
2. Creates destination directory if missing
3. Copies `roles/openshift_gitops/helm/` to destination
4. Renders operator manifests with **4-tier sequential sync-wave strategy**
5. Renders Ansible Automation Platform extra resources (if selected)
6. Renders Mac VLAN policies per NVIDIA Network Operator config (if selected)

## Directory Structure

```
roles/openshift_gitops/
├── apps/                                    # OLM/YAML-based operators
│   ├── cert-manager-operator/               # Tier 1: Foundations (-40)
│   ├── external-secrets-operator/
│   ├── openshift-nmstate/
│   ├── openshift-kmm/
│   ├── cisco-intersight/
│   ├── lldpd/
│   ├── openshift-cluster-observability-operator/  # Tier 2: Observability (-30)
│   ├── openshift-opentelemetry-operator/
│   ├── openshift-tempo-operator/
│   ├── openshift-nfd/
│   ├── openshift-sriov-network-operator/
│   ├── nvidia-network-operator/             # Tier 3: GPU/Hardware (-20)
│   ├── openshift-cnv/
│   ├── openshift-jobset-operator/           # Tier 4: AI/Scheduling (-10)
│   ├── openshift-kueue-operator/
│   ├── openshift-lws-operator/
│   ├── openshift-keda/
│   ├── openshift-connectivity-link/
│   └── aap/
├── helm/                                    # Helm-based operators (Tier 3 & 4)
│   ├── nvidia-gpu-operator/                 # Tier 3: GPU Stack (-20)
│   └── redhat-ods-operator/                 # Tier 4: AI Platform (-10)
└── templates/
    ├── nvidia-gpu-operator.yaml.j2          # Helm Application (sync-wave: -20)
    ├── redhat-ods-operator.yaml.j2          # Helm Application (sync-wave: -10)
    ├── cisco-ai-pods-apps.yaml.j2           # ApplicationSet for apps/*
    └── ...                                  # Other supporting templates
```

## 4-Tier Sequential Sync Wave Strategy

To build a highly resilient OpenShift AI infrastructure, all **21 operators** are organized into a **4-tier sequential rollout strategy**. This prevents cluster-wide race conditions by ensuring dependencies are fully healthy before dependent components deploy.

### Why Sync Waves Matter

OpenShift AI stacks have **hard dependencies** between layers:
- **GPU drivers** can't run before **node configuration** is ready
- **GPU Operator** can't detect hardware before **Node Feature Discovery** tags nodes
- **Red Hat OpenShift AI** can't initialize before **GPUs, networking, and scheduling** layers are operational

Without proper sync-wave ordering, operators deploy in random order → resource conflicts → pod CrashLoopBackOff → cascading failures across the entire cluster.

### Tier 1: Core Platform Foundations (Sync Wave: `-40`)

**Components:** `cert-manager`, `external-secrets`, `openshift-nmstate`, `openshift-kmm`, `cisco-intersight`, `lldpd`

**Why First:**
- **`cert-manager`**: Issues all TLS certificates and validates webhooks. Thousands of validating/mutating webhooks from downstream operators depend on this being operational first.
- **`openshift-nmstate`**: Configures kernel network interfaces and namespaces. SR-IOV, bonding, and VLAN tagging must exist before hardware can use them.
- **`openshift-kmm` (Kernel Module Management)**: Compiles and injects out-of-tree kernel drivers (needed by NVIDIA DOCA drivers later). Must run before hardware-specific drivers load.
- **`cisco-intersight`**: Manages firmware/hardware discovery. Foundation for infrastructure visibility.

**Deployment Logic:**
```
Wait for all Tier 1 → 100% Healthy & Ready → Then proceed to Tier 2
```

### Tier 2: Observability & System Networking (Sync Wave: `-30`)

**Components:** `cluster-observability`, `opentelemetry`, `tempo`, `nfd`, `sriov-network-operator`

**Why Second:**
- **`nfd` (Node Feature Discovery)**: Labels worker nodes with CPU, PCI, and GPU capabilities. The **NVIDIA GPU Operator** cannot detect where to run driver DaemonSets until NFD has scanned and tagged all nodes.
- **Observability Stack** (`opentelemetry`, `tempo`): Provides trace collection and telemetry pipelines that all subsequent operators integrate with for debugging and monitoring.
- **`sriov-network-operator`**: Configures physical SR-IOV functions for high-performance networking. Required by NVIDIA Network Operator for GPU-to-GPU InfiniBand/RoCE.

**Deployment Logic:**
```
Tier 1 ✓ → Deploy Tier 2 → NFD labels all nodes → Tempo pipelines ready → Then proceed to Tier 3
```

### Tier 3: Hardware Acceleration & Mesh (Sync Wave: `-20`)

**Components:** `nvidia-gpu-operator` (Helm), `nvidia-network-operator`, `openshift-cnv`

**Why Third:**
- **`nvidia-gpu-operator`**: Deploys NVIDIA GPU drivers, CUDA runtime, and device plugins. Requires:
  - NFD labels (Tier 2) to find where to run drivers
  - KMM (Tier 1) to load kernel modules
  - Cert-manager (Tier 1) for driver validation webhooks
- **`nvidia-network-operator`**: Configures NVIDIA DOCA drivers for GPU-to-GPU and GPU-to-storage networking. Depends on:
  - SR-IOV (Tier 2) for physical network function provisioning
  - GPU Operator (same tier) for NVIDIA fabric manager integration
- **`openshift-cnv`** (Virtualization): Provides VM container networking mesh for service routing. Required by RHOAI for multi-pod communication.

**Deployment Logic:**
```
Tier 2 ✓ → Deploy Tier 3 GPU stack → GPUs detected & drivers loaded → Network operator configures fabric → Then proceed to Tier 4
```

### Tier 4: AI Platform, Scheduling, & Apps (Sync Wave: `-10`)

**Components:** `redhat-ods-operator` (Helm), `jobset`, `kueue`, `leader-worker-set`, `keda`, `aap`, `connectivity-link`

**Why Fourth (Last):**
- **`redhat-ods-operator` (RHOAI)**: The user-facing AI platform. Requires everything below to be operational:
  - GPUs (Tier 3) for Jupyter compute
  - GPU networking (Tier 3) for distributed training
  - Scheduling components (Tier 4) for multi-node ML jobs
  - Observability (Tier 2) for job tracing
- **`jobset`, `kueue`, `leader-worker-set`**: Advanced Kubernetes workload scheduling for multi-node AI training and parameter servers. RHOAI uses these to safely schedule complex ML workloads.
- **`keda`**: Kubernetes Event-driven Autoscaling. Scales training pods based on queue depth or custom metrics from ML workloads.
- **`aap` (Ansible Automation Platform)**: Automation framework for infrastructure provisioning after the AI cluster is ready.

**Deployment Logic:**
```
Tier 3 ✓ (GPUs + Network ready) → Deploy Tier 4 → RHOAI spins up Jupyter notebooks with GPU access → Scheduling operators enable multi-node training → Complete ✓
```

## Sync Wave Annotation Details

Each operator has a `deploymentWave` in its `config.json`:

```json
{
    "config": {
        "deploymentWave": "-40"
    }
}
```

This translates to an ArgoCD `sync-wave` annotation:
```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-40"
```

ArgoCD processes sync-waves in ascending order:
- `-40` executes first
- `-30` waits until `-40` complete
- `-20` waits until `-30` complete
- `-10` waits until `-20` complete

## Helm-Based Operators

Two operators are deployed via Helm charts with direct ArgoCD Applications (not the ApplicationSet):

| Operator | Type | Tier | Sync Wave | Template |
|----------|------|------|-----------|----------|
| `nvidia-gpu-operator` | Helm | 3 | `-20` | [nvidia-gpu-operator.yaml.j2](templates/nvidia-gpu-operator.yaml.j2) |
| `redhat-ods-operator` | Helm | 4 | `-10` | [redhat-ods-operator.yaml.j2](templates/redhat-ods-operator.yaml.j2) |

These have no `config.json` in `apps/` — their sync-wave is defined directly in the template via:
```yaml
annotations:
  argocd.argoproj.io/sync-wave: "-20"
```

## Files

| File | Description |
|------|-------------|
| `tasks/main.yaml` | Role entry point for GitOps content generation |
| `defaults/main.yaml` | Role defaults (empty) |
| `helm/` | Helm charts (copied to destination) |
| `templates/cisco-ai-pods-apps.yaml.j2` | ApplicationSet for `apps/*` operators |
| `templates/nvidia-gpu-operator.yaml.j2` | Helm Application for GPU Operator |
| `templates/redhat-ods-operator.yaml.j2` | Helm Application for RHOAI |
| `templates/nic-cluster-policy.yaml.j2` | NVIDIA Network Operator cluster policy |
| `apps/*/config.json` | Operator metadata (deploymentWave, etc.) |

## Key Variables

Set in `host_vars/openshift/operators.ezai.yaml`:

| Variable | Description |
|----------|-------------|
| `openshift.destination_directory` | Output path (default: `_generated_gitops`) |
| `openshift.base_dns_domain` | Cluster base DNS (default: `example.com`) |
| `openshift.cluster_name` | Cluster name (default: `default`) |
| `openshift.operators.openshift_gitops.gitops_repo_url` | **Required** — GitOps repo URL |
| `openshift.operators.openshift_gitops.prune` | Auto-prune (default: `false`) |
| `openshift.operators.openshift_gitops.self_heal` | Auto-heal (default: `true`) |
| `openshift.operators.nvidia_gpu_operator.gpu_operator_version` | GPU Operator version (default: `gpu-operator-certified.v26.3.0`) |
| `openshift.operators.redhat_ods_operator.replicas` | RHOAI replicas (default: `1`) |
| `openshift.operators.nvidia_network_operator.mac_vlan` | Mac VLAN network policies |

## Idempotency

Safe to re-run. Existing files are reconciled with current variable values.

## Validation

Verify sync-wave ordering:
```bash
grep -r "deploymentWave" roles/openshift_gitops/apps/*/config.json | sort
grep -r "sync-wave" roles/openshift_gitops/templates/*.yaml.j2
```

Check ArgoCD Application sync order:
```bash
# After applying to cluster:
oc get applications -n openshift-gitops -o custom-columns=NAME:.metadata.name,SYNC-WAVE:.metadata.annotations.argocd\\.argoproj\\.io/sync-wave | sort -k2 -n
```

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
