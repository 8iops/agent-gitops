# Native v0.16.18 copied-store readability

Run this suspended Job only after restore-local-v2 succeeded. It copies only the
accepted baseline/database into the empty working/database. It never mounts the
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
in the 0700 state/native-v01618 directory; never tail it into the task. No registry
scan, full export or account-content output is requested.

Require native exit 0, filter exit 0, Complete and the allowlisted result. Retain
the state marker and counts for later comparison, accounting for the native
NodeId lease update. These gates establish copied-store readability, not user
mail/calendar/file correctness or token isolation. They do not execute v0.16.27's
normal startup migration path; that remains a separate reviewed phase.

Apply/render this directory separately from restore resources. Run only one
rehearsal Job at a time. Bounded resources and zero API/network access remain.
