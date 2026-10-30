# Final conversion on an isolated, stopped source copy

This suspended Job runs the official pinned migrate 1.0.3 `run --final --yes`
using the same answered state and target as the completed non-final conversion.
The source is an isolated v0.16.27 copy, not the live production store, and its
normal-startup Job has stopped cleanly. This is an **isolated rehearsal final**;
production keeps serving on the original version. No ServiceAccount token or
network access is present. Native stdout, stderr, report and answers remain on
the restricted state PVC.

The guard requires completed answered-prepare, non-final run and pre-final full
verify markers, an unused final stage, and regular source/target RocksDB files.
It refuses a second attempt after any partial final stage, preserving evidence.
The official final command performs its own 30-second source change check,
copies queue/tasks/spam model and samples verification. No `--allow-errors` or
`--force-after-final` is used. The bounded verifier returns only fixed status,
requires native exit zero and presence of the private final report, and does
not claim post-final full verification, target startup or rollback.

Before execution, confirm the pre-final full verify Job completed and no other
Job or server has either store open. Read back the static migration-store
ConfigMap and PVCs, render/server-dry-run the ConfigMap and suspended Job,
apply/read back, then unsuspend only this Job. Never print native logs or
reports. Preserve any partial target and state on failure. A distinct reviewed
post-final full verify must pass before any v1 server startup. The 43 removed
role permission entries and 12 SpamTags still require an operational decision.
