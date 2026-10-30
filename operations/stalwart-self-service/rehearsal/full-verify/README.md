# Full native verification of isolated forward conversion

This suspended Job runs official migrate 1.0.3 `verify --full` only after the
isolated non-final conversion Job completed. Source and target PVCs are both
read-only. Only the restricted state PVC is writable, for native stdout,
stderr and exit evidence. No ServiceAccount token or network access is present;
the existing rehearsal deny-all policy selects the Pod.

The guard requires successful answered-prepare and forward-run exit markers,
an unused full-verify stage and both RocksDB stores. Native output remains on
the restricted PVC. The only console output is fixed success/failure JSON.
Native exit zero is the acceptance condition for this full verification; it
does not prove target server startup, OAuth compatibility, rollback or
production readiness. A failed or partial target is preserved for inspection.

Before execution, confirm the forward-run Job completed and no other Job is
opening source or target. Verify the existing static migration-store ConfigMap,
render/server-dry-run this ConfigMap and suspended Job, apply/read back, then
unsuspend only this Job. Never print native logs or reports via platform tools.
The 43 removed role permission entries and 12 SpamTags still need an explicit
compatibility decision, even if native full verification succeeds.
