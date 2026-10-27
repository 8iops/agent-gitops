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

The live gateway still references retired Dex SSO. This adoption records that
existing dependency; it does not deploy or restore Dex. SSO retirement remains
separate work and must preserve authenticated administration. API readiness is
not evidence that SSO login works. Do not mark that dependency resolved merely
because this release is accepted.
