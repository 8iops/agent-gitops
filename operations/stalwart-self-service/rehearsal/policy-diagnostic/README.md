# Shape-only diagnosis of failed policy projection

The first policy-projection Job failed closed and its evidence remains intact.
This new suspended Job uses the same read-only state and signed Python image.
It neither runs native prepare nor opens a database. It returns only fixed stage/
reason identifiers, known prompt/field names, JSON types, null/presence flags,
lengths/counts and whether the existing strict field validator accepts the shape.
It does not print values, object IDs, map keys, source lines or parser exceptions.
Even a complete diagnostic keeps policyApproved=false; it never selects answers.

A definite deployment defect was found independently of private input: Kubelet
ConfigMap projections are symlinks, while the original main read public vocabulary
with the private-state no-symlink reader. A separate bounded public-vocabulary
reader now permits that fixed reviewed ConfigMap projection; private state retains
O_NOFOLLOW, parent symlink rejection, file-type and size checks. The diagnostic
imports the exact updated validator, with byte-equality tests to prevent drift.
A realistic ..data symlink fixture covers the deployment failure. No context
validator is relaxed based on this finding.

Official 0.16.27 schema represents requireScopes as Map<String>, whose serializer
emits an object with boolean values (including {} when empty), not null. Duration
serializes u64 milliseconds. requireAudience is nullable. Migration auth.rs copies
those available source values into compact-JSON comments. Actual diagnostic
shapes must be observed before proposing any compatibility exception.

Only the new Job name stalwart-rehearsal-policy-diagnostic-v1 may be run after
review. Preserve the original failed Job and state. Diagnostic success is not
successful original projection or a migration acceptance result. Any malformed
or unexpected shape remains blocked; no raw logs are needed for this step.
