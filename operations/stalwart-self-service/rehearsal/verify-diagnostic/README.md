# Bounded diagnostic for failed pre-final full verification

The isolated non-final conversion Job completed, but the native `verify --full`
Job returned nonzero. Upstream `GlobalCheck::Shared` excludes final-only global
categories, so failure is not automatically explained by pending finalization.
This suspended, one-shot Job reads only the private verification state PVC,
mounted read-only. It does not open source/target databases, run migration,
read credentials, or access the network or Kubernetes API.

The script returns only a fixed result and numeric counts from the official
`verify: N accounts checked, M mismatches, U not explained ...` line, if
present. V2 also tests only four fixed upstream error signatures in stdout:
target open, source open, read-only filesystem, and missing answers; it returns
booleans, never matching text. It does not emit raw logs, status text, object
IDs, account names or report entries. Stderr is never read; only its presence
is reported. No output marks verification accepted.

The v1 diagnostic completed with no summary and empty stderr; V2 retains that
Job and uses a new name. Before execution, confirm the failed verify Job's exact UID, Pod and native
exit file stage, render/server-dry-run the ConfigMap and suspended Job,
apply/read back, then unsuspend only this Job. Inspect only its JSON output.
Do not proceed to final run, target startup or production cutover until the
failure is classified and corrected in a separate reviewed change.
