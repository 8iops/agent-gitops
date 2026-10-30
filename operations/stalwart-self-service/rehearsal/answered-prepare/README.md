# Answered native prepare on an isolated v0.16.27 copy

This suspended Job uses the official immutable migrate 1.0.3 image and the
same read-only rehearsal source as the discovery Job. It does not run migration,
create a target, or touch production. The existing candidate private file is
copied to a fresh state directory, and native `prepare --non-interactive` must
exit zero. Raw stdout, stderr, answers, and report remain on the restricted
state PVC. No ServiceAccount token or network access is present; the rehearsal
deny-all policy selects the Pod.

The verifier compares the parsed native answers with the original candidate,
requires all six questions answered, zero errors, exactly 12 dropped objects,
and bounded source counts. Logs contain only fixed status and counts. A second
attempt cannot overwrite the directory. A failure never becomes migration
approval. The 43 removed old role permissions and 12 SpamTags still need
review after actual converted target inspection.

Apply only after candidate Job completion and review, no concurrent RocksDB
user, rendered manifest review, and server dry-run. Unsuspend only this Job.
Do not print private files or use its state for production. A separate reviewed
PR must define target conversion, verification, and rollback rehearsal.
