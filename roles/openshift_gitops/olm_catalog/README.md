# OLM Catalog Notes

This document captures key behavior and troubleshooting guidance for OLM catalog content used by the OpenShift GitOps workflow.

## Table of Contents

- [OLM Catalog Notes](#olm-catalog-notes)
  - [Table of Contents](#table-of-contents)
  - [Key Considerations for OpenShift 4.21](#key-considerations-for-openshift-421)
  - [Troubleshooting](#troubleshooting)

## Key Considerations for OpenShift 4.21

- Sync Waves: Use `sync-wave: "0"` for the operator and `sync-wave: "1"` for the NMState instance. This prevents Argo CD from applying NMState before the CRD is registered.
- SkipDryRunOnMissingResource: Set this option in the Argo CD application so initial sync does not fail before the NMState kind exists.
- Singleton Instance: The NMState resource is a cluster-wide singleton and should only exist once as `nmstate`.

[Back to Table of Contents](#table-of-contents)

## Troubleshooting

- Argo CD sync fails for NMState custom resources:
  - Confirm the operator application sync wave is lower than the NMState instance sync wave.
  - Ensure `SkipDryRunOnMissingResource=true` is set on the NMState application.
- NMState CRD not found:
  - Verify the NMState operator application is healthy and CSV is `Succeeded` before syncing the instance.
  - Re-sync operator app first, then sync NMState instance app.
- Duplicate NMState resources detected:
  - Remove extra NMState instances and keep only the singleton `nmstate` object.

[Back to Table of Contents](#table-of-contents)
