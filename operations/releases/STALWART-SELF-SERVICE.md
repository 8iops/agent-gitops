# Stalwart self-service delivery

The Re8ch self-service integration is coordinated in the 8iops organization.
Repository ownership and runtime ownership remain separate:

| Concern | Existing repository and source |
| --- | --- |
| User-scoped bindings, mail/calendar/file tools | `re8ch/service-backend`, `platform/apps/tenant-mcp/` |
| Restricted management tools | `re8ch/service-backend`, `operations/cloud-platform/` and the current module publication allowlists |
| Stalwart runtime and client access contract | `8iops/agent-gitops`, `clusters/re8ch/mail-authority-resources.yaml` plus reviewed Kustomize patches |
| Tenant MCP runtime, module registry and self-service routes | `siren-observer/observability-gitops`, `clusters/re8ch/charts/birfucate-metering/` and `contracts/observability-chart-birfucate-metering-tenant-infrastructure.yaml` |

Do not duplicate the tenant-api Deployment in this repository or change its
authority as a side effect of adding collaboration tools. The existing
`tenant-go-release` source workflow builds the application image. Preserve its
immutable digest and provenance; the runtime authority consumes that artifact.
Its legacy source-repository image ConfigMap update alone is not deployment
evidence for the current cloud SSA release.

## Current change

`stalwart-client-discovery-patch.yaml` corrects the existing bot access contract
to discover CalDAV/CardDAV collections and use a provider account identifier for
WebDAV. It preserves the original imported authority-transfer payload and its
digest. It does not enable new tools, provision user credentials, add OAuth
clients, alter routing, or claim that the application integration is deployed.

Validate the patch using the existing compiler and release checks:

```sh
python operations/releases/compile_domain.py
python operations/releases/compile_domain.py --check
python -m pytest -q tests/test_mail_authority_transfer.py tests/test_domain_compiler.py
python policies/validate.py
```

The resulting `agent-runtime-domain-mail-system` release retains the same 45
objects, existing-object guard, field manager and prune policy. Publish through
the existing `static-release` workflow only after the signed PR is reviewed.
Do not write the ConfigMap directly from a workstation.

## Application release gates

The candidate configuration is in `operations/stalwart-self-service/`. It is
deliberately outside the production root and keeps `COLLABORATION_ENABLED=false`.
The reviewed client ID is `re8ch-self-service`. The candidate client is not
first-party and permits only `mail`, `calendars` and `files` service scopes.
Device codes and tokens remain in user/organization-bound `stalwart-<opaque>`
broker Secrets; they are not runtime environment variables or MCP arguments.

**The pinned Stalwart v0.16.18 schema has neither `firstParty` nor `scopes` on
`x:OAuthClient`.** This was checked against the official release schema at
`https://raw.githubusercontent.com/stalwartlabs/stalwart/v0.16.18/resources/schema/schema.json.gz`
(compressed SHA-256 `553e7d7106f34c98febc62eea6024a6df35c7950f5368e987cc0dad52812654e`).
The newer upstream schema describes both fields, but that does not authorize an
unreviewed upgrade or establish current runtime support. Do not apply the
candidate registration to v0.16.18 or fall back to an unscoped/first-party token.

Use a sanctioned platform read to obtain the running provider's sanitized
schema and OAuth discovery metadata, then run the offline preflight:

```sh
python operations/stalwart-self-service/provider_preflight.py \
  --schema /path/to/provider-schema.json \
  --metadata /path/to/oauth-metadata.json
```

Passing only permits a native CLI dry-run of the candidate after the deployment
version is reviewed. Then validate effective client settings and a real scoped
test token: exact requested service scopes, no `urn:stalwart:jmap` management
capability, correct provider account, and denial of ungranted data operations.
Schema compatibility never replaces that authorization test. Only after all
gates and source-image checks pass may the runtime authority enable the feature.

1. Merge tested binding and protocol implementations in the source repository.
   The application must check organization and subject ownership, individual
   capability consent, expiry and revocation on every data request.
2. Build once in GitHub Actions. Record the real image digest, source commit,
   attestation and successful validation run. Never insert a placeholder digest.
3. Update the actual tenant runtime authority with the immutable image and exact
   required non-secret configuration. Provision missing credentials through the
   approved broker; only names, scopes and rotation rules belong in Git.
4. Update the MCP publication allowlist and capability discovery in the same
   coordinated release. Verify both the internal and public self-service
   endpoints. Management tools remain in the independently authorized platform
   catalog, unavailable to ordinary members.
5. Use an explicitly authorized test account to verify mail search/read,
   calendar query and an intentional test RSVP, a shared small file read, then
   revoked access. Validate same-organization other-user denial as well as
   cross-organization denial. Do not record message or file contents in CI logs.
6. Record runtime image identity, release acceptance and MCP evidence in the
   existing release operation/issue. A merged PR, tool listing, or mock protocol
   test alone is not successful end-to-end deployment evidence.

Stalwart settings or endpoint changes use this repository's existing Mail
contract. Tenant deployment changes use the observability repository's existing
contract. New global RBAC and credential provisioning remain platform-owned;
runtime executors must not gain broad Secret or RBAC writes to simplify rollout.
