# Full native verification of isolated forward conversion

This suspended Job runs official migrate 1.0.3 `verify --full` only after the
isolated non-final conversion Job completed. The source PVC is read-only. The
target PVC is writable only so the official `V1Target::open_with_rewrite` can
initialize its RocksDB registry and lock/WAL. The restricted state PVC holds
native stdout, stderr and exit evidence. No ServiceAccount token or network access is present;
the existing rehearsal deny-all policy selects the Pod.

The guard requires successful answered-prepare and forward-run exit markers,
an unused full-verify stage and both RocksDB stores. Native output remains on
the restricted PVC. The only console output is fixed success/failure JSON.
Native exit zero is the acceptance condition for this full verification; it
does not prove target server startup, OAuth compatibility, rollback or
production readiness. A failed or partial target is preserved for inspection.

The v1 Job failed before comparison because its target PVC was mounted
read-only. A bounded v2 diagnostic confirmed both the target-open and
read-only filesystem signatures without exposing native logs. This new Job
name and state stage retain the v1 failure evidence. No source or production
mount is made writable.

Before execution, confirm the forward-run Job completed and no other Job is
opening source or target. Verify the existing static migration-store ConfigMap,
render/server-dry-run this ConfigMap and suspended Job, apply/read back, then
unsuspend only this Job. Never print native logs or reports via platform tools.
The 43 removed role permission entries and 12 SpamTags still need an explicit
compatibility decision, even if native full verification succeeds.
