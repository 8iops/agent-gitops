# Fresh-copy v0.16.27 startup v2

The first normal-startup attempt failed after about 65 seconds without readiness.
Its stdout/stderr were empty. The successful earlier console probe took about 67
seconds. Official boot performs storage/directory/Core parsing before enabling
telemetry, with bounded external OIDC discovery retries; normal mode also need
not have a console tracer. These facts justify a longer bounded observation,
not a claim that any particular directory caused the failure.

This new suspended Job first copies the read-only accepted baseline into a new
`startup-v2/database` subdirectory on the existing working PVC. It rejects any
existing destination, verifies the full directory contents with diff, and retains
the previous failed `/database` and `/state/startup-v01627` untouched. Only one
worker may run. The Job deadline is 600 seconds including copy/pull/shutdown;
readiness probing has a wall-clock 180-second budget after process launch.

Fixed observations include process-alive, HTTP numeric response code counts,
LISTEN counts on 443/8080 and SYN_SENT count. No addresses, process arguments,
environment, fd paths, native logs or response bodies are returned. These counts
are clues, not proof of an OIDC failure. Deny-all networking remains required;
no role, directory setting, public origin or credential is changed. Background
tasks can still mutate this disposable copy internally.

Only exact HTTP 200 followed by SIGTERM and native exit 0 accepts the phase.
A fresh failure never produces an ACCEPTED marker or triggers retry/prepare.
Accepted marker: `/state/startup-v01627-v2/ACCEPTED`, content
`ready-and-cleanly-stopped`. All subsequent native migration source configs must
use `/var/lib/stalwart/startup-v2/database`; prepare-discovery's separate PR must
use this same marker and path. `workers.yaml` now names this path, but it remains
unapplied and must not run before acceptance and conversion-policy review.

This historical rehearsal remains unsuitable for production promotion; final
cutover still requires a new stopped-source generation and full verification.
