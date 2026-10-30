# Post-final full verification of isolated migration

This suspended Job runs pinned official migrate 1.0.3 `verify --full` after a
successful isolated `run --final --yes`. It requires native final exit zero and
presence of the private `final-report.txt`. The source v0.16.27 rehearsal PVC
is read-only. The isolated v1 target PVC is writable only because the official
v1 target adapter initializes RocksDB and needs its lock/WAL; the state PVC is
writable for private native logs. No production PVC, network or ServiceAccount
token is present. The rehearsal deny-all policy selects the Pod.

The Job has a unique name and state stage, preserving pre-final verification
evidence. Native stdout and stderr remain private. Only fixed success/failure
JSON is emitted; success means the official full comparison exited zero after
finalization. It does not establish target server startup, OAuth compatibility,
rollback or production readiness. The 43 removed role permission entries and
12 SpamTags still need explicit review.

Before execution, confirm final-run Job Complete and no other source/target
opener. Render/server-dry-run ConfigMap and suspended Job, apply/read back,
then unsuspend only this Job. Never print native logs or reports. A failed
verification preserves target and state for a bounded diagnostic.
