# Cube recovery preparation (not deployable yet)

CompoCV requires Cube recovery before its persistent test environment.
Tracking: https://github.com/compocv/compocv/issues/5 (private product repository).
Platform preflight: https://github.com/re8ch/service-backend/pull/2493.

R640's non-mutating preflight completed with exit code 0 and reported both a
KVM device and CPU virtualization flags. Storage observation found every PG
active+clean. The owner authorized a fresh Cube data set and retirement of old
Cube volumes after replacement acceptance.

`values.yaml` is a draft overlay for upstream CubeSandbox commit
`8721dd151971ce3c2966482bbd32904ad98f378e` (v0.6.0 images). It is deliberately
NOT included in the active cluster root or a release contract. Credential
markers are render inputs, never usable passwords. Do not apply its Helm output.
`images.lock.json` records anonymously resolved registry manifest digests.
The image tags in upstream chart output still require replacement with these
digests before publishing a release artifact.

The recovery uses fresh names and paths, cephfs-r640, ordinary KVM, no PVM
host installer, no module loading, no KVM permissions rewrite, and no public
Ingress or CoreDNS edits. Existing Cube PVCs are not referenced.

Remaining preparation gates:

- Bound credential provisioning inside the platform; no plaintext in Git or logs.
- Render deterministic runtime manifests, omit Helm-generated credentials, and
  arrange managed certificates and exact node/RBAC authorization.
- Verify upstream scripts respect the separate host paths and do not alter the
  host container runtime or existing guest state.
- Publish through the existing signed release workflow with exact resource
  scope, then verify sandbox creation, execution, pause/resume and persistence.
- Only after Cube acceptance, deploy CompoCV and its isolated test database;
  run Stalwart feedback -> private Issue/Project -> improvement PR verification.

No recovery workload or product environment has been deployed by these files.
