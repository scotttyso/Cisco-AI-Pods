# Phase 4A: Compute Provisioning and Lifecycle Baseline

[Back to Best Practices README](README.md) | [Back to README](../README.md)

## Executive Summary

Phase 4A defines how compute nodes are provisioned, standardized, and lifecycle-managed so that training clusters (B300/H200) and inference clusters (RTX6000/RTX4500) behave predictably at scale. The goal is to remove configuration drift before workload onboarding.

## 1. Intersight Policy Model for Repeatable Provisioning

Use Cisco Intersight templates as the source of truth for server identity, firmware, BIOS, boot order, and network policy.

### Core Best Practices

1. Build role-based Server Profile Templates:
   - Training template (B300/H200)
   - Inference template (RTX6000/RTX4500)
2. Pin firmware versions to validated releases.
3. Version control template exports after every approved change.
4. Apply changes in maintenance waves (canary -> rack -> fleet).
5. Enforce naming standards by role, rack, and sequence.

### Why This Matters

- Prevents drift between nodes in distributed jobs.
- Reduces MTTR by making node state reproducible.
- Allows safe scale-out without manual per-node tuning.

## 2. BIOS and Platform Tuning by Workload Class

### Training Nodes (B300/H200)

Optimize for sustained throughput and stable collective performance:
- Performance-focused power profile.
- Deterministic CPU frequency behavior.
- NUMA-aware tuning and PCIe consistency.
- SR-IOV/IOMMU enabled where required by design.

### Inference Nodes (RTX6000/RTX4500)

Optimize for latency consistency and serving density:
- Balanced power policy for steady response time.
- IRQ and NUMA alignment for model-serving processes.
- Deterministic network and storage interrupt handling.

## 3. Provisioning Workflow (Day-0 to Day-1)

1. Claim hardware in Intersight.
2. Attach role-specific profile templates.
3. Verify firmware and BIOS compliance.
4. Validate out-of-band access and inventory health.
5. Stage OS install profile per node class.
6. Execute post-provision smoke tests.

## 4. Storage and Boot Policy Alignment

Define storage policy by node role to avoid contention and boot inconsistencies.

### Recommended Pattern

- OS volume isolated from model/data paths.
- Training nodes:
  - optimize for sequential ingest and checkpoint write throughput.
- Inference nodes:
  - optimize for model load latency and cache hit efficiency.

### Practical Guidance

- Keep local boot mirrors consistent across rack groups.
- Avoid mixed boot controller modes within the same cluster.
- Reserve local fast storage tiers for hot artifacts and temporary staging.

## 5. Compute Provisioning Validation Checklist

- [ ] Node inventory matches intended role mapping.
- [ ] Template policy attachment successful on all targets.
- [ ] Firmware/BIOS versions are identical by role.
- [ ] OS provisioning completes without manual intervention.
- [ ] Baseline network/storage checks pass.
- [ ] Host telemetry visible in observability stack.

## 6. Troubleshooting Guide

### 6.1 Profile Attachment Fails

- Probable causes:
  - Resource pool exhaustion.
  - Invalid policy reference.
  - Dependency mismatch between template objects.
- Actions:
  1. Validate pool availability and association constraints.
  2. Reconcile referenced policy versions.
  3. Retry on one canary node before bulk apply.

### 6.2 Firmware Drift Across Nodes

- Probable causes:
  - Auto-update not disabled on subset.
  - Out-of-band prior manual updates.
- Actions:
  1. Export and diff firmware inventories by role.
  2. Re-apply pinned baseline policy.
  3. Hold workload rollout until parity is restored.

### 6.3 Unexpected Performance Variance

- Probable causes:
  - BIOS mismatch.
  - NUMA/CPU policy mismatch.
  - Mixed power profile.
- Actions:
  1. Compare BIOS exports from a known-good node.
  2. Reapply standardized template to outliers.
  3. Re-run synthetic baseline tests before workload tests.

### 6.4 Inference Latency Regression (RTX6000/RTX4500)

- Probable causes:
  - CPU interrupt imbalance.
  - Storage cache pressure.
  - Unintended thermal throttling.
- Actions:
  1. Pin IRQ affinity for serving interfaces.
  2. Validate model cache placement and local disk pressure.
  3. Check thermal policy and host-level throttling telemetry.

## 7. Phase Completion Checklist

Do not advance to Phase 4B until:
- [ ] All compute nodes pass provisioning checks.
- [ ] Role-specific template compliance is green.
- [ ] Firmware and BIOS parity confirmed.
- [ ] Baseline host metrics collected and archived.

## Summary

Phase 4A is complete when provisioning is deterministic, repeatable, and validated by role. That foundation is required before deeper GPU runtime optimization in Phase 4B.
