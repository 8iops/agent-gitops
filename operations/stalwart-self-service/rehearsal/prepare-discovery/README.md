# Native prepare discovery, without approving answers

Apply this directory separately after review. The Job starts suspended and is
not part of the production root. Require the 0.16.27 startup Job Complete, its
clean-stop ACCEPTED marker and no other process holding the working RocksDB.
Do not run this alongside the older generic prepare Job in workers.yaml.

The native init container opens only the accepted source PVC read-only, executes
prepare once into a new private state directory and keeps all raw output there.
It mounts no target store. The subsequent Python container mounts state read-only
and emits only fixed status fields, aggregate counts and known prompt names.
It never returns object IDs, comments, recommended answers or configuration.
Its image reuses the signed Cloud Platform artifact built from service-backend
14dc5b1eeb8607057882d8f8d6ca35667eb4f485 (workflow 41038794961), pinned in PR2535;
command override invokes Python 3.12 directly, not the platform server. Pod UID
2000 permits access to native private state; no API token/credentials are mounted.

Registry access was checked without login credentials: the anonymous standard
registry challenge returned this exact manifest HTTP 200 and matching digest.
mail-system has no dockerconfigjson Secret and its default ServiceAccount has no
imagePullSecrets (metadata audits op_fecf622fc7c54348a1ac31380be23850 and
op_3f9f9f4c4d824da89d321cb86628f9a4). No new Secret or copied credentials are
needed. Actual node reachability/image pull remains unverified until the Job runs;
a pull failure must be diagnosed, not bypassed with local credentials. Verify
the rehearsal deny-all NetworkPolicy exists before unsuspending.

Native exit 1 is classified as questions_pending only if both native outputs
exist, answers contain no accepted tables, a unique valid summary has no errors,
no unreadable objects are reported, and every problem exactly matches an
unanswered allowlisted prompt. Missing files, malformed output, unfamiliar prompt,
conversion error, abort, accepted answer or unexpected native exit fail closed.
The filtered success is evidence discovery, not successful migration or policy
approval. Warnings/drops remain counts requiring restricted operator review.

No retries overwrite evidence: stage /state/prepare-discovery-v1 must not exist.
Preserve failures before any separately reviewed rerun. The initial filter
intentionally returns no issuer/audience/client values; obtain further fields
only through a subsequently reviewed allowlist after learning actual questions.
See CONVERSION-POLICY.md for native capability limits and consumer compatibility.

Validation: tests exercise secret sentinel exclusion, invalid/extra/missing
problems, conversion failures, unreadable source, actual answers, oversized files,
symlinks, duplicate/unknown questions and native code mismatch. These tests do
not claim an actual provider discovery result.
