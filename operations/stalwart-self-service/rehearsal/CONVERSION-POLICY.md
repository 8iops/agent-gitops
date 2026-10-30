# Conversion policy review for migrate 1.0.3

Status: preparation only. This document does not authorize `prepare`, migration,
provider writes, or production cutover. There is deliberately no runnable
`answers.toml`: the restored registry and existing OAuth client contracts have
not yet been projected and reviewed. An isolated rehearsal is not production
acceptance, and its old cold snapshot must never become the production target.

## Exact upstream contract

Reviewed sources are [1.0.3 prompts](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/mapping/prompts.toml),
[answer parser](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/crates/mapping/src/answers.rs),
[prepare](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/crates/migrate/src/prepare.rs)
and [migration requirements](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/README.md).
Use the reviewed immutable worker digest, not a floating tag.

Answers use TOML `version = 1`. Global answers use `[global.<prompt>]`;
instance answers use exact discovered object keys, for example
`[instance.http_forwarded."x:Http"]` and
`[instance.oidc_directory."x:Directory/<actual-id>"]`. Do not invent IDs.
A catalogue default is a recommendation, not approval. Non-interactive prepare
fails with unanswered questions; run also refuses unanswered questions. Retain
this fail-closed behavior. Generated reports and answers are restricted state,
not safe Git attachments: they can contain inherited configuration and secrets.

The standard official build includes enterprise support even without a license;
selecting an OSS migration build because no license is installed can drop data.
Source must first complete the separately reviewed 0.16.27 startup transition.

## Decisions that must remain explicit

| Prompt | Upstream default or change | Required review |
| --- | --- | --- |
| categories | All 16 categories | Preserve settings, principals, mail, calendars, contacts, files, sieve, identities, push_subscriptions, spam_samples, reports, archive, spam_model, queue, tasks, telemetry. Do not omit categories to pass validation. Queue/tasks/spam model finalization requires stopped source. |
| blob_store | External blobs `reuse` | Discover backend first. Rehearsal cannot share writable production blobs; use an independently provisioned copy, verify capacity and path mappings. Internal data-store blobs are copied automatically. |
| changed_defaults | `recommended` mixes pin/inherit | Review every affected property. `pin` is a review starting point, not an approved final policy. |
| new_permissions | `grant` | Review exact old-to-new permissions and affected roles. `none` avoids implicit grants but can break metadata/connected-app functionality; neither choice is approved yet. |
| oidc_directory | unscoped `interoperable` | Resolve issuer, audiences, token kind and consumer contract before choosing. Never silently replace this with `reject` across existing authentication. |
| oauth_registration | `accept` | v1 rejects arbitrary unregistered client IDs and always allows rate-limited public RFC7591 registration. Inventory and register required existing clients; review changed public-registration semantics explicitly. |
| oidc_token_lifetimes | `clamp` | Code/access minimum 600000 ms; refresh idle timeout minimum 86400000 ms. Review actual values and renewal semantics before increasing them. |
| http_forwarded | X-Forwarded-For, one hop | Verify actual trusted proxy chain and header overwrite behavior. Do not infer hops from hostname or default. |
| counter_read | Drop expression | Review each expression; rewrite adds counter mutations and can create unbounded keys. Abort unresolved cases. |
| in_memory_cluster / enterprise_on_oss | Replacement/drop decisions | Do not invent Redis credentials or accept object loss. Stop for backend/edition review. |

For the new self-service OAuth client, require explicit mail/calendars/files
scopes and no management capability. That client policy is distinct from an
OIDC directory's handling of external tokens and from id.re8ch.com acting as an
OIDC provider for existing applications. An `openid email` login request does
not prove a mail API token should be accepted, and does not prove login breaks
under a particular directory policy. Trace the actual consumer first.

Directory policy must record exact `accepted_audiences`,
`skip_audience_validation`, `opaque_token_validation` (none/userInfo/introspection),
`unscoped_tokens` (reject/interoperable/full), `allow_id_token_claims`,
`lenient_issuer_match`, `allow_invalid_certs`, and `claim_name`. Keep validation
exceptions false unless separately justified. Do not select opaque validation
from guesswork; introspection may require server-side credentials. `full` is
not an acceptable shortcut. Rejection of unscoped tokens is a candidate only
for a confirmed compatible directory, not a global migration default.

## Native capability assessment and preferred projection path

Prefer the already pinned official migrate worker plus the existing reviewed
Python runtime image. Do not build a Rust reader as a prerequisite. The official
CLI provides prepare, run, verify, status, report and rollback; there is no
standalone inspect command in the documented command inventory. `status` and
`report` describe migration state/issues, not a complete source configuration.
Native server export is a full data backup, not a bounded JSON configuration
projection; introducing an export decoder would add unnecessary format work.

Official `prepare.rs::source_objects` already reads typed source registry objects
and converts them in memory. `write_outputs` emits `answers.toml` and
`prepare-report.txt`, not the complete converted settings. The answer writer
includes contextual values and suggested defaults in comments; unanswered tables
remain commented out (tested upstream in `unanswered_questions_are_written_commented_out`).
Exact execution order in [commands/run.rs](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/crates/migrate/src/commands/run.rs):
load absent answers as empty, open source, collect registry objects, validate,
print summary, `write_outputs`, then test `prepared.is_complete()` to choose
exit 0 or 1. Thus unanswered questions do not prevent restricted output files.
Earlier source-open errors do prevent those outputs. `PrepareArgs` has no JSON
output option; global JSON log format is logging, not a settings export.
`status --format json` and `report --format json` exist for migration state,
but do not replace prepare's question inventory. Source opening calls
`RocksDbStore::open_with_mode(..., RocksDbOpenMode::ReadOnly)` in
[source-v016 open.rs](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/crates/source-v016/src/open.rs).
Therefore prepare is useful evidence discovery even when its expected result is
unanswered questions. It is not the migration `run`, and recording its restricted
state does not approve any policy. No prepare execution is authorized by this PR.

Preferred next reviewed operation:

1. Require accepted readability (schema 6 / propertyRecords 1986), completed
   0.16.27 normal startup and clean stop. Serialize all RocksDB users; never open
   the working database while startup or another migration worker is active.
   Use the existing reviewed worker source configuration and isolated state
   directory, immutable image, deny-all networking and no production PVC.
2. Run ONLY `prepare --source <reviewed-source-config> --state <new-private-state>
   --non-interactive` in that worker. Keep stdout/stderr, answers and report on
   restricted PVC with umask 077. No target/run/final/rollback invocation and no
   fabricated answers. A return code of 1 is not automatically success: require
   complete native output files and classify unanswered questions separately
   from source-open, validation or conversion errors. Otherwise fail closed.
3. In a separate existing signed Python runtime worker, mount that state read-only
   and parse bounded files (maximum 1 MiB each, maximum 100 questions). First
   return only counts and allowlisted prompt identifiers/object keys, never raw
   report lines or comment text. Treat TOML comments as untrusted text: use exact
   version-pinned syntax recognizers for individual known context fields, reject
   unknown shapes, and never uncomment the whole file into accepted answers.
   Any field not reliably present remains explicitly unknown. Fixed error codes
   only; no parser exceptions containing input. Tests must prove sentinel secrets
   cannot escape via success, errors, unknown fields or limit failures.
4. Apply the allowlist below only to fields actually available from these native
   outputs. The concrete gap is that prepare reports decisions/changes rather
   than all unchanged properties or all registered OAuth clients. Do not infer
   absent clients/properties from absent questions. Fill remaining OAuth consumer
   metadata from reviewed nonsecret application declarations and an existing
   platform-mediated, server-side property-selective management read when the
   isolated endpoint is ready. Credentials and complete API responses stay on
   the server; no token is passed in tool argv or returned to the model.
5. Only if these native paths demonstrably cannot supply a required field should
   a separate PR propose a one-shot typed registry reader. Document the exact
   missing field and why property-selective native/API access cannot provide it.
   Such a fallback would use official 0.16.27 RegistryStore getters on a disposable
   copy, never server main or unrestricted registry serialization. It is not
   implemented or selected by this document.

The initial projection should identify which decisions actually trigger before
choosing implementation for the remaining fields. Preserve raw state for audit,
but do not attach it to GitHub or tail it through platform tools. Emit a new
schema-versioned JSON object with snapshot identity, native/Python image digests,
completeness flags and bounded counts. The native console's raw scan/get output
is not an approved configuration projection.

Allowlist, derived from official 0.16.27 `crates/registry/src/schema/structs.rs`:

| Object | Permitted projection |
| --- | --- |
| Directory, OIDC variant only | Object key/id, variant, issuerUrl sanitized to HTTPS origin/path without userinfo/query/fragment, requireAudience, requireScopes, claimUsername/claimName field names. Other variants: type and count only. No description, groups, tenant membership or credentials. |
| OidcProvider | requireClientRegistration, anonymousClientRegistration, authCodeExpiry, accessTokenExpiry, refreshTokenExpiry, refreshTokenRenewal, userCodeExpiry, idTokenExpiry; normalize durations to integer milliseconds. Never encryptionKey/signatureKey. |
| OAuthClient | Count and stable object IDs; match requested known clientId against a separately reviewed consumer inventory in memory and output match booleans. Redirect origins/counts only after rejecting userinfo/query/fragment; no secret, contacts, description, full redirect URI or arbitrary client metadata. |
| Http | useXForwarded and rateLimitAnonymous structured rate. Do not emit responseHeaders, redirectRoot or arbitrary expressions. For allowedEndpoints emit presence plus comparison result against a reviewed expected expression, not raw expression text. |
| SystemSettings | defaultHostname and services map of known protocol names to sanitized hostnames. No arbitrary properties. |
| BlobStore/DataStore | Backend variant, internal-versus-external flag, path-is-inside-approved-copy-root boolean. No endpoint query, credentials, bucket contents or full configuration. |

Strings must pass syntax/length validation before emission; malformed URLs or
unexpected values produce a fixed error, not the original string. Object IDs
and issuer/audience values remain access-controlled metadata; the public PR
contains only policy, not the actual projection.

The exact typed schema is available in
[0.16.27 structs](https://github.com/stalwartlabs/stalwart/blob/v0.16.27/crates/registry/src/schema/structs.rs)
and [registry getters](https://github.com/stalwartlabs/stalwart/blob/v0.16.27/crates/store/src/registry/get.rs).
The preferred native-output filter and platform execution plan still require
review and tests before use. This document claims no projection execution result
and does not request a new image build.

## Existing login contract and production decision gate

The restored provider registry cannot tell us scopes requested by every relying
party or the real proxy chain. Supplement its projection with reviewed nonsecret
consumer configuration: expected issuer, client ID registration match, audience,
requested scope names, flow, redirect origin/path equality boolean, token kind
and whether an external OIDC Directory is actually used. Do not retrieve tokens,
client secrets or user claims. Examine gateway trust configuration for header
sanitization and hop count; values cannot be inferred from the stored useXForwarded
boolean alone. Absence of a client object is not evidence that no client exists:
v0.16 may have accepted arbitrary unregistered client IDs.

For each consumer of id.re8ch.com, record a compatibility result and an explicit
policy decision before producing production answers. Preserve existing login
behavior only where understood and reviewed; do not enable full unscoped access
to avoid a test failure. Native OAuth tokens are not migrated: reauthentication
is expected and must be tested, not confused with an outage.

Rehearsal may use TCP peer addressing and isolated fixture clients; mark those
answers rehearsal-only. It must not send external mail or contact real external
OIDC directories. Production answers require actual proxy/consumer contracts,
user-consented login verification, retained rollback state, and a newly frozen
source capture/final synchronization with full verification. Never promote the
old rehearsal snapshot or treat fixture consent as existing-login acceptance.
