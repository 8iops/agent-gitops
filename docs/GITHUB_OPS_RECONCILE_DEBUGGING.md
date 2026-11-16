# Agent reconcile debugging

The authoritative cross-domain procedure is the service-backend
[GitHub Actions to Kubernetes reconciliation runbook](https://github.com/re8ch/service-backend/blob/main/docs/GITHUB_OPS_RECONCILE_DEBUGGING.md).

For `agent-runtime-reconcile.yml`, open the jobs rather than inferring the cause
from the badge or the last log lines. The selector reads the exact
`ssa-state-<release>` ConfigMap before it creates release jobs. A
`state-read-failed` warning therefore means that accepted-state read failed; it
does not prove an OCI signature, ToolHive, or executor failure.

Compare the reviewed `operations/releases/domain-access.yaml` and platform RBAC
with the live Actions OIDC identity. Check both the namespaced state ConfigMap
permission and any cluster-scoped resource permission, such as a CRD
ClusterRoleBinding, using the exact group and resource name. Never restore local
Flux, broaden wildcard access, disable TLS verification, rebuild an accepted
artifact, or force shared field ownership as an incident shortcut.

Dispatch the repaired workflow through the Re8ch Admin GitHub Governance service
and retain its audit reference. Recovery is complete only when the newest `main`
run is terminal success, every selected release is accounted for, and runtime
read-back agrees with accepted state.
