# Native v0.16.18 copied-store readability

Run this suspended Job only after restore-local-v2 succeeded. The first attempt already copied the
accepted baseline/database into working/database, then native exec failed with
exit 126. The v2 attempt preserves that copy and first compares every directory
and file against the read-only baseline; it does not overwrite failed evidence. It never mounts the
production source. The original v0.16.18 console can update its NodeId lease, so
only this working copy is writable; the baseline is read-only.

Preconditions require nonempty CURRENT and a MANIFEST file before opening the
store. A fixed memory config explicitly names /var/lib/stalwart/database;
CONFIG_PATH is unset so CLI parsing is not bypassed, and --console is last.
The command stream ends in quit because EOF alone can loop. No empty-store
bootstrap or implicit config path is accepted.

The original native console reads the known public schema key p\x00, whose
v0.16.18 value must be big-endian schema 6, and scans the property key range for
an aggregate count greater than one. Its scan prints values, so raw stdout goes
only through a FIFO into an allowlist awk filter and is never stored or returned.
The filter emits schemaVersion/propertyRecords/status only. Startup stderr stays
in the 0700 state/native-v01618-v2 directory; never tail it into the task. No registry
scan, full export or account-content output is requested.

Require native exit 0, filter exit 0, Complete and the allowlisted result. Retain
the state marker and counts for later comparison, accounting for the native
NodeId lease update. These gates establish copied-store readability, not user
mail/calendar/file correctness or token isolation. They do not execute v0.16.27's
normal startup migration path; that remains a separate reviewed phase.

Apply/render this directory separately from restore resources. Run only one
rehearsal Job at a time. Bounded resources and zero API/network access remain.

## Narrow native exec correction

The official v0.16.18 Dockerfile sets cap_net_bind_service=ep on the binary. The
first probe dropped all capabilities and failed at native exec. The existing
production StatefulSet uses drop ALL plus only NET_BIND_SERVICE; v2 follows that
same narrow bounding set while retaining non-root, no privilege escalation,
read-only root filesystem, no API token and deny-all networking. No source
workload security setting changes.

Before invoking native code, v2 checks only the fixed Operation not permitted
classification in the previous restricted stderr, then runs a full recursive
content/directory comparison against baseline (no output or values returned).
If either check fails it stops. Symlinks are rejected. The prior state directory
and copied data are retained, and all new status/stderr uses native-v01618-v2.
After these gates the same FIFO filter and native checks run unchanged.

Read-only evidence of the existing source capability setting:
`audit://operations/op_3d29e931cf3343659eb95a5f62fefd41`.
First probe safe failure result:
`audit://operations/op_cf43c0fb0a8b41f4809c30853ab92643`.
This is an exec correction, not evidence of native database readability yet.
