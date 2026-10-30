# Restricted conversion-policy evidence

This separately applied, suspended Job reads only the already completed native
prepare state. It never opens a database, runs prepare again, changes answers,
starts Stalwart, or executes migration. Existing state is mounted read-only; no
fsGroup ownership adjustment, API token, external credentials or writable volume
is present. Use the existing rehearsal deny-all policy. Reuse the exact signed
Cloud Platform Python image from prepare-discovery; no build or dependency install.

Input is fixed to `/state/prepare-discovery-v1/native`. The known evidence is
2927 objects, 12 dropped objects, 63 warnings and six unanswered prompts, one each
of categories, changed_defaults, new_permissions, oauth_registration,
oidc_directory, oidc_token_lifetimes. Any changed summary or accepted answer
fails closed. This is a snapshot-specific projection, not a generic config reader.

## Exact native formatting and output bounds

Upstream migrate 1.0.3 `mapping/src/answers.rs::write_prompt` emits source context
as `# Source <label>: <compact JSON>` BEFORE the commented unanswered table.
`transform/auth.rs` supplies precisely issuerUrl/requireAudience/requireScopes/
claimName for OIDC directories, two registration booleans, and ONLY token
lifetimes below v1 minimums. Parse only that source context, never recommended
values or the v1 explanatory text. claimName is ignored. Objects are identified
internally for matching problems but their IDs are not emitted.

The output contains HTTPS issuer without userinfo/query/fragment, a bounded
simple audience identifier, the original scope-to-boolean map, registration
booleans and observed integer lifetime milliseconds. Unsupported URL/audience
forms fail closed for review rather than being echoed. An absent field is
explicitly unknown; absent durations are not reconstructed from defaults.
Native context does not identify the actual consumer token kind, so tokenType
always remains unknown. No token, secret, client credential or user-claim field is selected for output;
raw input can contain sensitive comments and is treated as private in memory.

Upstream `mapping/src/report.rs::Display` defines change entries. This filter
returns only object type, top-level schema property name, fixed change code and
count for warning entries, plus dropped-object counts per type. Object types and
property names must occur in the bundled public official 0.16.27 schema
vocabulary (source and SHA-256 recorded in vocabulary.json). Dynamic map keys,
object IDs, original values, reasons and free-form descriptions never escape.
Unknown shapes/names/codes contribute only unknown counts and remain blocked.
Raw report/comment text is never returned. Each file is bounded at 1 MiB, question
count at 100, and the known summary bounds report entries. The complete missing
answer list must exactly match the six tables; no conversion errors are accepted.

Source references:
- https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/crates/mapping/src/answers.rs
- https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/crates/mapping/src/transform/auth.rs
- https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/crates/mapping/src/report.rs

## Decisions stay blocked

Even fully parsed output has policyApproved=false and
blocked_pending_review. Supabase-issued webmail tokens and Stalwart-as-provider
login clients are different contracts. Do not globally choose reject for
unscoped tokens, accept public registration changes, clamp durations, grant new
permissions or approve drops merely because this Job completes. Compare observed
issuer/audience/scopes against the reviewed actual consumer configuration first.
Missing token-kind evidence, incomplete warning classification and any unknown
field require further bounded review. This Job does not edit production or make
an OAuth compatibility claim.

`new_permissions` has no source context: official auth.rs calls ask_global,
and engine/mod.rs::global_answer passes Vec::new() for context. Therefore the
projection explicitly marks permissionMatches unknown. Recommended grant
defaults are not evidence of existing enabled/disabled/credential matches. The
same mapping can affect enabled permissions, disabled permissions and credential
permission lists; current aggregate warning counts cannot authorize any choice.
