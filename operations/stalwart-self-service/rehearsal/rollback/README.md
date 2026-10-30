# Reverse migration rehearsal on isolated stores

This suspended Job runs official pinned migrate 1.0.3 `rollback --verify-full
--yes` from the **isolated v1 rehearsal target** into a new empty v0.16
rollback PVC. It reads the completed forward state required by the official
reverse converter. Production is never mounted, stopped or changed. The v1
startup rehearsal must have stopped cleanly first. No Kubernetes token or
network access is present; the rehearsal deny-all policy selects the Pod.

The v1 source is mounted read-only; only the new rollback target PVC and
restricted state are writable. The guard requires final and post-final full
verify markers, clean v1 server stop, regular target RocksDB files, and an
unused rollback state/target. Native stdout/stderr remain private. The official
`--verify-full` flag requires complete reverse comparison before exit zero;
there is no `--allow-errors` or shared-blob deletion shortcut. A fixed result
reports only native success and new rollback store presence.

This proves a reversible path for the isolated snapshot, not production
rollback readiness. A separate v0.16.27 startup on the reverse store, OAuth
and mail/calendar/file compatibility, and fresh production cutover still need
review. The 43 removed role permission entries and 12 SpamTags remain explicit
policy decisions. If official rollback refuses because a shared blob store
requires a choice, stop and review backend evidence; do not add permissive
flags automatically.

Before execution, verify v1 startup Job Complete and no store opener; check
the static migration-store ConfigMap and rollback PVC. Render/server-dry-run
the ConfigMap and suspended Job, apply/read back, then unsuspend only this
Job. The rollback PVC may be Pending before scheduling under local-path
WaitForFirstConsumer. Preserve failed target/state, and never print native logs.
