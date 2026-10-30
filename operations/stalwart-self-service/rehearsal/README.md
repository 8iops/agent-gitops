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
4. Copy accepted baseline into source-v01627. Use the pinned official v0.16.27 and stalwart-migrate v1.0.3 images
   listed below, matching edition/architecture and the existing artifact trust
   policy. No placeholder digest or arbitrary download-at-runtime Job is used.
5. Upgrade only the working copy to v0.16.27. Run official prepare and run against
   an empty target-v1, retaining state on migration-state. Map source/target paths
   explicitly. Stop all copy writers before final; run full verification.
6. Validate migrated v1 data and scoped client behavior in isolation. Rehearse
   rollback into rollback-v01627 with forward state, record losses and compare
   aggregate integrity results. Do not overwrite the baseline or production data.

Suspended worker templates are supplied below. A follow-up signed PR may enable
individual phases and scoped test access only when the backup reference, capacity
and operator-approved policies are known. Only then can a separate production
cutover PR and approval be concrete.

## Pinned workers, source upgrade and precise execution order

`upstream-artifacts.json` records public registry manifest digests independently
hashed on 2026-10-30. The official migration container exists as
`docker.io/stalwartlabs/stalwart-migrate:1.0.3` (without a `v` prefix). Reuse it;
no custom build, downloader or second publishing service is needed. Registry
hash verification proves immutable bytes, not publisher-signature verification;
check the existing release artifact trust policy before admitting these images.

`workers.yaml` contains an exact RocksDB config and five **suspended** Jobs,
separate from the resource Kustomization. They use the pinned official migration
image, UID/GID 2000, no API token, dropped capabilities, read-only root filesystem,
bounded resources/time and no retries. Every source is a copy, mounted read-only.
No Job is permitted to mount the baseline or a production PVC.

The official v1.0.3 README expressly requires v0.16.27 and says earlier versions
must first be upgraded. Its converter vendors the v0.16.27 schema. Do not run it
directly on v0.16.18. Rehearsal upgrades the copied store first; whether production
needs an intermediate online upgrade or a stopped copied-store upgrade is a
separate decision after the copy rehearsal proves integrity and downtime.

Execute these reviewed phases, through the platform plan/write path:

1. Restore the accepted v0.16.18 archive into baseline, verify it, then copy to
   source-v01627. Start the pinned v0.16.27 server against only that working copy
   using `/config/source.json` and deny-all networking. Preserve UID/GID 2000.
   Confirm upgrade completion from restricted startup evidence and stop cleanly.
   No real SMTP, OAuth, replication or external OIDC access is allowed.
2. Apply worker configurations as suspended, then resume `migrate-prepare` only.
   Its `prepare --non-interactive --source /config/source.json --state
   /state/forward` intentionally fails until required policy answers are reviewed
   and supplied to durable state. A failed Job is inspected and explicitly
   recreated after correcting the cause; automatic retries remain disabled.
3. Resume `migrate-run` only after answers are accepted. It copies to the empty
   target-v1 store. Keep all copied-source server processes stopped before
   `migrate-final`, whose explicit `--yes` is authorized only for this isolated
   stopped copy. Do not execute the same arguments against live production.
4. Resume `migrate-verify` (`verify --full`). Require success, no unexplained
   mismatches and reviewed conversion warnings. Start pinned v1.0.1 against the
   target copy for isolated integrity and OAuth tests, then stop it cleanly.
5. Resume `migrate-rollback` with `--verify-full`, targeting only the empty rollback-v01627 claim and
   retaining `/state/forward`. Require success before starting v0.16.27 on that
   copy. Compare data counts and documented v1-only losses.

No worker runs before backup restoration, source upgrade and operator policy
answers. The activeDeadlineSeconds limit is 30 minutes per phase, not a claimed
migration time. Retain state when interrupted and diagnose before resuming.

## Concrete cold-backup approval scope

Read-only `du -sk /var/lib/stalwart` returned **265888 KiB (about 260 MiB)** on
2026-10-30 (`audit://operations/op_328e5eba2ddd4d2e859129ba87bf2d73`). This is
allocated filesystem size, not an integrity check or elapsed-time estimate.
The running official image has tar, cp, sha256sum and du
(`audit://operations/op_475abe331aa14e48904b56ecace4b926`).

If no accepted external backup exists, request one controlled backup-only
maintenance window, provisionally 10 minutes with a 5-minute copy abort threshold
and remaining time for source restart/health verification. Pre-stage storage and
images first. Confirm actual read throughput before accepting this estimate.
Impact: mail, DAV and the `id.re8ch.com` OAuth provider served by stalwart-flk may
be unavailable; users may be unable to sign in, and queued mail must be retained.
Do not touch stalwart-idp-flk. The proposed actions are:

1. Record exact StatefulSet UID/resourceVersion/replicas, source PVC binding,
   ready endpoint, imageID, relevant writer CronJob suspension states and queue
   status. Confirm all external blob dependencies and snapshot consistency.
2. Through a reviewed maintenance release, stop source write traffic and suspend
   the three Stalwart writer/reloader CronJobs, retaining previous states. Wait
   for in-flight Jobs to finish; do not delete an active writer blindly. Scale
   only stalwart-flk from 1 to 0 and wait for pod termination and clean shutdown.
3. In mail-system, run a separately reviewed one-shot backup Job using the exact
   current official image, read-only source PVC, UID/GID 2000, no API token or
   network, and a new 4Gi staging PVC. Archive the whole store to
   `/backup/stalwart-v01618.tar`, compute SHA-256 to a sidecar manifest, sync and
   verify the checksum. Neither file names nor data contents belong in job logs.
   Local-path affinity keeps that reader on the source volume's node. No hostPath.
4. On success or copy timeout, terminate the backup reader first, then restore
   original replicas, CronJob states and traffic. Verify ready endpoint, original
   imageID, OAuth metadata and mail/DAV health. No source image or DB upgrade is
   part of this window. If source cannot restart, hold traffic and recover from
   the unchanged source using the recorded desired state; escalate before any
   replacement or destructive restore.
5. Retain the staging copy and transfer its checksum-verified archive to the
   approved encrypted independent backup destination, using broker-held access.
   Resolve that destination and retention before approving the window. A single
   RBD staging copy is not a durable disaster-recovery backup. Restore the archive
   into rehearsal baseline and require integrity acceptance before migration.

Fresh native CephCluster evidence at 2026-10-30T09:19:48Z reports approximately
2.15 TB available, but HEALTH_WARN: one BlueStore OSD has slow operations and five
pools lack replicas. Audits `audit://operations/op_10f1dde000dc4229a5b20c08d094d93b`
and `audit://operations/op_ee564ff660c543d285a03a5846013dae`. The 17Gi rehearsal plus
4Gi backup staging request needs **21Gi** and an explicit storage-risk acceptance;
these raw capacity figures do not prove pool replication or restore performance.
No production freeze, backup Job, claim or worker has been executed.

Backup destination discovery remains unresolved: the global ObjectBucketClaim
inventory is empty (`audit://operations/op_e9b3ac6a01384ba8b75bc049a0267f83`).
The existing Harbor S3 backup uses a Harbor-owned Secret reference and its last
success was 2026-06-20 (`audit://operations/op_3341b079f5f24a139a38138754fe3f8e`).
That is neither current backup-health evidence nor permission to reuse Harbor
credentials for Stalwart. Obtain a platform-approved opaque backup accessRef,
encryption and retention policy before requesting the cold-copy outage.
