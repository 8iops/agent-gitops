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

## Safe restored-copy projection: implementation contract

This is a precise design for a subsequent reviewed worker, not an instruction
to run an unrestricted console dump or expose full objects through the model.
The native console's raw `scan`/`get` output is unsuitable for configuration
projection. No full registry export, token decoding output, or config dump may
be attached to GitHub or returned by the platform tool.

1. The accepted readability result is schema 6 / propertyRecords 1986. Run stages
   serially: the 0.16.27 startup process must terminate cleanly before a reader
   or copy opens its RocksDB files; never share an active RocksDB directory.
   Use a new disposable copy of the accepted restored database, with CURRENT
   and MANIFEST prechecks and complete copy verification. Baseline mounts remain
   read-only. No production PVC, production route, source listener or external
   directory connection is allowed. Retain deny-all networking and no API token.
2. Build a small one-shot reader against the exact official 0.16.27 source and
   pin its artifact. Use `RegistryStore::init(config, false)` and typed
   `RegistryStore::get`/`list` from `crates/store/src/registry/get.rs`; do not call
   the server main, start services, initialize defaults, or invoke migrate.
   RocksDB opening can write engine files, so only the disposable copy is writable.
   Verify schema 6 before reading and reject missing/empty/unexpected stores.
3. Match only the object types below. Typed objects may contain secrets in
   process memory; construct a NEW output structure field by field. Never
   serialize the source object, stringify native errors, or print Debug output.
   Bound collection reads/output (maximum 100 directory/client objects and
   64 KiB total); exceedance fails with a scalar classification, not truncation
   presented as complete. A paginated implementation may be reviewed separately.
4. Emit one schema-versioned JSON projection with snapshot identity, reader
   digest, completeness flags and counts. Errors contain only fixed codes.
   Stderr stays in mode-0700 restricted state, without log tailing. Tests must
   insert sentinel secrets into every excluded field and prove neither success
   nor failure output contains them; test unknown variants and limit failures.

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
The one-shot reader still needs implementation, tests, immutable artifact
review and a platform execution plan before use; this document claims none of
those execution results.

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
