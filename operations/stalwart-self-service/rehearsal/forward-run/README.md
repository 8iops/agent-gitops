# Non-final conversion on an isolated copy

This suspended Job runs the official pinned migrate 1.0.3 `run` command using
the completed answered-prepare state. It reads only the isolated v0.16.27
source PVC and writes only the separate rehearsal v1 target PVC and restricted
migration state. It does not use `--final`, send mail, modify production, or
start a v1 server. No ServiceAccount token or network access is present; the
rehearsal deny-all policy selects the Pod.

The shell guard requires the accepted 0.16.27 startup marker, native prepare
exit zero, existing answers and report, an unused run state directory, an empty
v1 target database path, and a regular source RocksDB manifest. The native
console output remains private on the state PVC. A second run cannot silently
reuse a partial target or state. The verifier returns only fixed booleans and
checks that a target RocksDB was created. This is not full migration
verification or rollback evidence.

Before execution, confirm the answered-prepare Job completed successfully and
no other Job is opening the source or target. Read back the existing
`stalwart-rehearsal-migration-store-config` and both PVCs against the reviewed
declarations. Render and server-dry-run this ConfigMap and suspended Job,
apply them, read back exact mounts and image, then unsuspend only this Job.
Inspect its bounded JSON completion log; never print native stdout, stderr,
answers or report. Keep any partial target for investigation if the run fails.

Next gates: full native `verify`, target server startup and OAuth/service
compatibility, final queue/tasks synchronization on a stopped fresh copy,
rollback rehearsal, and a separately reviewed fresh production cutover. The
43 removed role permission entries and 12 SpamTags remain unresolved.
