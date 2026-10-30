# 0.16.27 normal startup rehearsal

Run this suspended Job only after `native-v01618-v2/ACCEPTED`, with no other
rehearsal Job active. It uses the already accepted disposable working database,
never the production PVC or read-only baseline. Apply this directory separately;
it is not in the production root. Review and merge precede application.

The pinned official image runs normal `--config` startup, waits for loopback
`/healthz/ready`, sends SIGTERM and requires exit 0 before writing `ACCEPTED`.
The existing 300-second Job deadline also bounds a hung graceful shutdown;
deadline termination is failure, never acceptance. No API token is mounted.
Only status scalars return in Job logs; raw native output stays in restricted
state files and must never be tailed through the platform tool.

This proves the actual 0.16.27 startup path on a copy, not a schema version
change: both releases use structure version 6. There is no official upgrade-only
startup mode. Selective deny-all egress blocks external sends, but background
tasks can change the working copy internally. No uncreated ClusterRole or
environment variable is claimed to disable those tasks. The immutable baseline
and original source remain separate. This copy is never promoted to production.

After completion, verify Job Complete, aggregate result and no remaining worker
before another phase. Conversion policy and non-secret source projections are
separate prerequisites; this Job does not execute `prepare`, migration or cutover.
Final production cutover requires a new freeze and fresh source generation as
documented in the parent rehearsal README.

References: official [0.16.27 image](https://github.com/stalwartlabs/stalwart/blob/v0.16.27/Dockerfile)
includes curl and the same HTTPS 443 / HTTP 8080 loopback fallbacks; this probe
requires readiness instead of the image's liveness check. Official
[`request.rs`](https://github.com/stalwartlabs/stalwart/blob/v0.16.27/crates/http/src/request.rs#L587)
returns HTTP 200 for a configured data store and 503 otherwise. The probe accepts
exactly 200; redirects are not followed or accepted, and response bodies are discarded.
