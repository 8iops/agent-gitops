# Read-only failed-startup classification

The v0.16.27 startup attempt failed with `readiness_not_observed`; it has no
acceptance marker. This separate suspended Job mounts only its state PVC,
read-only, and returns byte counts and fixed vocabulary match counts from the
restricted stdout/stderr. It never starts Stalwart, opens a database, accesses
production or prints a log line. No fsGroup ownership adjustment, network,
API token, writable volume or added capability is required.

A match is a diagnostic candidate, not a confirmed cause. Zero matches do not
prove absence of an error. Production uses HTTP 8080 `/healthz/ready` and the
public-origin environment setting; neither is changed by this diagnostic.
Apply and run once only after the failed startup worker has terminated. Retain
its original files. Any revised startup or deeper projection requires a separate
reviewed change; prepare remains gated on successful clean startup.
