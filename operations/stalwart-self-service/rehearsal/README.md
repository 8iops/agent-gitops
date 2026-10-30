# Isolated Stalwart migration rehearsal resource proposal

Not included in `clusters/re8ch`. Do not apply until the platform plan approves
capacity, backup access and retention. This proposal allocates no workload,
Service, public route, production PVC mount or credentials. The existing cloud
SSA executor remains the delivery mechanism; no local kubectl apply.

## Observed source, 2026-10-30

- `id.re8ch.com` and `collab.tools.re8ch.com` route to Service `stalwart`, whose
  sole ready endpoint is `stalwart-flk-0`. Audits:
  `audit://operations/op_9658c63889014ae78c4a4115fb8c74cd`,
  `audit://operations/op_a2895092e7884b0daced6bc2af81334d`.
- Pod imageID is `ghcr.io/stalwartlabs/stalwart@sha256:9ed1d343243b7aa72969e372a7240b7ddea07730781d4b68a0dc3d8d51c418bb`,
  matching the declared v0.16.18 image. Audit:
  `audit://operations/op_42007eeb350f46929aef20ef57c5e697`.
- Current PVC `mail-system/stalwart-flk-local-data` is Bound, local-path, 2Gi;
  mounted at `/var/lib/stalwart`. The checked-in config declares RocksDb.
  Audit: `audit://operations/op_694128811dea4e7ba4cb92a6a2b8c2e7`.
- No VolumeSnapshot in mail-system; no apparent Stalwart backup CronJob in the
  cluster inventory. These observations do not exclude external backups.
  Audits: `audit://operations/op_ab0ef41f903141cfbcb07f35b1036163`,
  `audit://operations/op_a879501860d74d7a9b53805f11d2bffc`.

Do not touch `stalwart-idp-flk` or infer the other existing RBD claims are valid
backups. Source image evidence now confirms the v0.16 migration prerequisite.
The id domain's consumers must still be inventoried before any production
maintenance: this proposal does not authorize an authentication outage.

## Resource and retention plan

Five new RBD claims request 17Gi total: four 4Gi stores (untouched restored
v0.16.18, working v0.16.27, empty v1 target, empty rollback target) and 1Gi durable
migration state. The 4Gi request gives headroom above the current 2Gi claim;
actual used bytes, free pool capacity and migration amplification must be checked
before allocation. Quota caps two pods, aggregate requests 2 CPU / 4Gi RAM and
limits 4 CPU / 8Gi RAM. No GPU, hostPath, production volume or external endpoint.
All ingress and egress are denied. Any temporary approved backup transfer route
needs a separate narrow NetworkPolicy and restricted credential reference.

Retain baseline backup, forward state and acceptance reports through cutover
and the approved rollback window. Proposed rehearsal expiry is seven days after
acceptance, requiring explicit review of backup retention before namespace/PVC
removal. Kubernetes quota and this document do not implement automatic expiry.

## Backup and restore acceptance before migration

1. Locate an existing backup by opaque reference and establish its timestamp,
   consistency method, checksum, encryption, restore procedure and coverage of
   data/blob stores and essential config/key references. Never output key values.
   If none exists, prepare a separately approved quiescence and cold-copy plan;
   copying live RocksDB files with tar is not a consistent backup method.
2. For a cold copy, inventory and pause all writers through reviewed maintenance,
   stop the source cleanly, copy the entire current source store plus any external
   blobs consistently, checksum the copy, and restore normal source operation.
   This requires its own outage approval and verified recovery procedure; do not
   execute it merely because this resource proposal was merged.
3. Restore into source-restore only. Confirm checksums and launch the exact pinned
   v0.16.18 in isolation with no SMTP, OAuth or external side effects. Record
   aggregate account/message/calendar/file counts and integrity results. Do not
   copy user contents to PRs/logs. A successful file copy is not restore acceptance.
4. Copy accepted baseline into source-v01627. A separately reviewed worker image
   must provide verified upstream v0.16.27 and stalwart-migrate v1.0.3 artifacts,
   matching edition/architecture, with provenance and immutable OCI digest. No
   placeholder digest or arbitrary download-at-runtime Job is supplied here.
5. Upgrade only the working copy to v0.16.27. Run official prepare and run against
   an empty target-v1, retaining state on migration-state. Map source/target paths
   explicitly. Stop all copy writers before final; run full verification.
6. Validate migrated v1 data and scoped client behavior in isolation. Rehearse
   rollback into rollback-v01627 with forward state, record losses and compare
   aggregate integrity results. Do not overwrite the baseline or production data.

Add the worker Job and scoped test access in a follow-up signed PR only when the
verified artifact, backup reference, capacity and operator-approved policies are
known. Only then can a separate production cutover PR and approval be concrete.
