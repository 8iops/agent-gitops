# Isolated Stalwart v1 normal startup rehearsal

This suspended Job starts the pinned official Stalwart v1.0.1 image against the
finalized and fully verified **rehearsal** target PVC. It has no Service,
hostNetwork, ServiceAccount token or external network access; the existing
rehearsal deny-all policy selects its Pod. Production keeps running on v0.16.
The target PVC is writable as required by normal server startup.

The script requires final-run and post-final full-verify exit-zero markers and
a regular v1 RocksDB store. It writes a small configuration to a memory
emptyDir, starts `/usr/local/bin/stalwart --config` (supported by pinned v1
source), probes only Pod loopback readiness on 443/8080 for at most 180 seconds,
then sends SIGTERM and requires a clean exit. Native stdout/stderr remain on
the restricted state PVC; only fixed status is printed. A unique state stage
prevents a second invocation from hiding partial evidence.

This proves normal startup and loopback readiness on the isolated copy. It
does not establish OAuth login, mail/calendar/file data access, delivery,
rollback, or production readiness. The 43 removed role permission entries and
12 SpamTags still need an explicit decision. Never attach this Pod to a public
Service or run it before final verification.

Before execution, confirm post-final verify Job Complete, no other process has
the target store open, and Cilium deny-all policy is realized. Render and
server-dry-run the ConfigMap and suspended Job, apply/read back, then
unsuspend only this Job. Inspect only fixed JSON output, not private logs.
