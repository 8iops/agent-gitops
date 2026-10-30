# Scoped OAuth migration readiness (issue #39)

Status: preparation only. Runtime version, live schema, native client dry-run,
backup restore and user-token isolation remain unverified. No image, storage,
routing or activation declaration changes are part of this preparation.

## Compatibility evidence

Official release schemas were inspected on 2026-10-30. The compressed schema
SHA-256 values below identify public upstream files, not runtime observations or
OCI image digests. Paths are `resources/schema/schema.json.gz` at the linked tag.

| Version | Compressed schema SHA-256 | OAuthClient compatibility |
| --- | --- | --- |
| [v0.16.18](https://github.com/stalwartlabs/stalwart/tree/v0.16.18) | `553e7d7106f34c98febc62eea6024a6df35c7950f5368e987cc0dad52812654e` | No firstParty, scopes or grantTypes |
| [v0.16.27](https://github.com/stalwartlabs/stalwart/tree/v0.16.27) | `3f3ca487e759e29eaa549ef056e950bf217bfb569107c7c8e867237493162b64` | No firstParty, scopes or grantTypes |
| [v1.0.1](https://github.com/stalwartlabs/stalwart/tree/v1.0.1) | `6b339146033eca792183bcaff209d0879c1e7b6e0c827c43b21e9f98afb4e9dd` | Explicit firstParty, OAuthScope set and OAuthGrantType set |

The v1 schema requires deviceCode in grantTypes to allow device authorization.
The non-first-party candidate therefore explicitly allows deviceCode and
refreshToken, and only mail, calendars and files scopes. This is a candidate
registration, never an instruction to apply it against the current deployment.

The [v1.0.0 release](https://github.com/stalwartlabs/stalwart/releases/tag/v1.0.0)
introduces scoped OAuth and an incompatible database layout. The
[v1.0.1 release](https://github.com/stalwartlabs/stalwart/releases/tag/v1.0.1)
includes additional consent changes. Upgrading the existing image on its current
PVC directly to v1 is not an admissible deployment plan.

## Required evidence and reviewed sequence

Use authenticated platform inspection, not workstation credentials, to capture:

- Both mail-system Stalwart workloads' declared image, observed imageID and
  readiness; their actual edition, data/blob backend and storage ownership.
- OAuth discovery issuer, scopes, grants and device/token endpoints; the running
  schema's OAuthClient field types and OAuthScope/OAuthGrantType enums only.
- Backup and restore results, storage capacity, queue status, external blob-store
  sharing, DNS/proxy assumptions and existing OIDC policy requirements.

The [official upgrade guide](https://stalw.art/docs/migration/upgrade-0-16/)
requires v0.16.27 as migration source. Prepare a separate reviewed patch upgrade
from the declared v0.16.18 first, using a verified OCI digest and rollback-tested
backup. This patch does not itself unlock scoped OAuth.

Use the [official migration utility v1.0.3](https://github.com/stalwartlabs/stalwart-migrate/tree/v1.0.3)
on an isolated restored copy before production. Select the matching edition and
architecture and verify its release checksum; a binary checksum is not an image
digest. Keep the migration state durable and access restricted. Review generated
configuration, especially OIDC audience/scope and proxy trust policies; do not
accept weakened defaults unattended.

Prepare and incrementally copy from v0.16.27 to a distinct empty v1 target store.
Map actual mounted paths explicitly. Rehearse final synchronization with all old
writers stopped, then full verification. Do not use error/mass-removal overrides
to force a failed migration through. Retain aggregate counts and failure status
as review evidence; reports and account data stay in restricted storage.

Only after restore and migration verification may a signed PR specify the real
v1 image digest, separate target storage references, maintenance cutover and
release acceptance criteria. Keep both provider nodes compatible before relying
on changed sign-in behavior. Rebuild search indexes and account for changed DAV
ETags and non-migrated OAuth tokens in the acceptance window.

## Rollback and activation

The [official migration README](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/README.md)
and [schema changes](https://github.com/stalwartlabs/stalwart-migrate/blob/v1.0.3/SCHEMA_CHANGES.md)
define rollback limitations. After v1 accepts writes, do not merely restart the
stale v0.16 store. Stop v1 writers and use the supported rollback conversion into
a fresh empty v0.16 target, with the original forward state. Drain queues and
review unsupported v1 fields, tasks and other losses before committing to
rollback. Shared external blobs need particular care: mutation or garbage
collection can invalidate an old-store fallback. Test this path on copied data.

After reviewed migration, run provider_preflight.py on sanitized live evidence,
then native dry-run and apply the reviewed OAuthClient candidate through the
platform plan/write workflow. Read back effective scopes and grantTypes.
Perform real device consent, refresh, exact-scope enforcement, management-denial,
other-user/tenant denial and revoke tests before enabling collaboration.

Repository authority remains: service-backend owns integration source,
8iops/agent-gitops owns Stalwart, and siren-observer/observability-gitops owns the
tenant runtime and publication. The existing cloud SSA release applies reviewed
immutable artifacts. Passing offline tests or merging this document is not
runtime acceptance and does not close #39.
