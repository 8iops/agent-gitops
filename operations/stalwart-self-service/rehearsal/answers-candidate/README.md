# Rehearsal-only conversion answer candidate

This suspended Job writes one private `answers.toml` to an isolated rehearsal
state PVC. It never reads the production store, invokes migrate, contacts a
provider, or writes an answer into Git. No ServiceAccount token or network
access is present; the existing rehearsal deny-all policy selects the Job.
The pinned projection ConfigMap must be the exact one that completed Job
`stalwart-rehearsal-policy-projection-v2`; verify its content before apply.

The script first repeats the complete bounded policy projection and pins the
observed six prompts, source counts, contexts, 43 removed role permission
entries, and 12 dropped SpamTags. It extracts exact instance keys only from
private `prepare` output. Changed evidence fails closed; logs contain only
fixed status and counts. The output file is mode 0600 and is never
returned through platform tools. A second run fails instead of overwriting it.

Candidate choices for an **isolated rehearsal**: all 16 categories; pin changed
defaults; add no new permissions until actual role mapping is tested; accept
OAuth registration behavior already enabled by the source booleans; retain
`authenticated` audience and UserInfo validation for the external OIDC
directory; allow only interoperable services for its OIDC-only scopes, with no
certificate, issuer, audience or ID-token validation exceptions; clamp the
8-hour refresh lifetime to the v1 1-day minimum. These are not production
answers. The 43 removed permission entries and 12 SpamTags require explicit
verification and operational decision before cutover.

Apply only after the source Job is Complete and no other RocksDB user is active.
Render and server-dry-run the ConfigMap and suspended Job, apply exact reviewed
resources, read back, then unsuspend only this Job. Inspect only its bounded
JSON log and completion status; never print the private `answers.toml`.
The next migration rehearsal must copy this answer into a separate private
state and retain the original unanswered prepare state for audit.
