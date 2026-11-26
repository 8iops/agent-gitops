# LiteLLM agent-domain adoption

`agent-runtime-domain-llm-gateway` adopts the existing five namespaced objects
through the shared SSA executor. The two Deployment UIDs, current image IDs,
public URL and MCP URL were verified through the platform before importing the
source from `service-backend/clusters/re8ch/components/llm-gateway/litellm.yaml`.
PostgreSQL and its init container now reference their current image digests.
No image is rebuilt. Namespace, storage, scheduling and Secret references remain
the existing runtime configuration. `requireExisting` and `prune: false` prevent
creation or deletion during adoption.

Evidence: `op_f127bdd727c84ef28d8338a6a518b912`,
`op_6d05c0d91cde4f7191a4522660e6fe11`,
`op_83f56dd55fba4319a92b29eae9d98aa5`,
`op_d54ef1be9efa4a5bae9458438c9725b9`.

The reviewed release replaces retired Dex SSO with the UserHub Supabase GoTrue
OAuth endpoints published through `https://db-rw.re8ch.com`. LiteLLM uses a
confidential client from the write-only `litellm-gotrue-sso` Secret, requires
PKCE, and accepts the exact callback
`https://litellm.service.re8ch.com/sso/callback`. The Secret payload is not part
of this repository or the signed release bundle. API readiness is not evidence
that SSO login works; completion requires an authorization-code login and UI
session probe through the public hostname.

`agent-runtime-domain-llm-gateway` remains the exact owner of the LiteLLM
Deployment. The separate `agent-runtime-exact-tenant-api-manager` release keeps
its existing field manager and only publishes the reviewed tenant API image and
`LITELLM_GATEWAY_URL`; it does not gain authority over the gateway or its
credentials.
