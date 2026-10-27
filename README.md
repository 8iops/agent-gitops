# RE8CH Agent GitOps

Private desired-state authority for the RE8CH Agent, ToolHive, and fast-moving tool runtime guardrails.

Product source and release artifacts remain in their product repositories. This repository pins signed immutable artifacts and cluster configuration only.

`contracts/agent-runtime-toolhive-operator.yaml` is the first static GitOps
shadow release. It compiles the reviewed render of the digest-pinned ToolHive
Operator chart into a deterministic OCI bundle, signs it with the protected
`release-executor-agent-runtime` workflow identity, and does not mutate the
cluster. Flux retains live ownership until dry-run, takeover, replay, health,
rollback, and zero-writer gates are separately proven.

## Cloud release artifact reuse

`static-release` defaults to `mode=publish` for a reviewed change. Use
`mode=reconcile` with `execute=true` to replay the target's healthy accepted OCI
digest without recompiling or publishing. Replays verify the original signer,
inventory and contract; blocked or suspended releases are rejected. Agent owner
migration requires an initial publication with the new canonical signer before
accepted-artifact replay can be used. State writes use optimistic concurrency.

Public pull request checks use GitHub-hosted workers. Private preparation can use
the restricted R640 fallback. Validation supersedes obsolete runs; deployment
runs remain serialized. No local Docker daemon is required by these workflows.

## Native domain cloud handoff

`python operations/releases/compile_domain.py` reuses the established SSA contract
and bundle validators to partition the production root by namespace. Generated
`contracts/*-domain-*.yaml` run through the existing `static-release` workflow.
`operations/releases/domain-access.yaml` is the exact reviewed access/state seed
for platform bootstrap; it is not included in this domain's runtime root.

The cohort report lists every source object, either in a publishable release or
with a specific remaining migration reason. Secret payloads and encrypted
configuration never enter public OCI bundles. Existing chart snapshot contracts
remain separate owners. Initial adoption permits only the exact reviewed object
inventory through `force_takeover=true`, after the previous writer is stopped.
Pruning is disabled during this first adoption; no migration deletes resources.

CI verifies deterministic outputs and compiles every generated contract. Actual
cloud adoption still requires the platform access seed and a successful release
run; generated bundles alone do not establish runtime ownership.

Role and RoleBinding desired objects remain platform-owned until admission can enforce their exact reviewed contents. Runtime groups receive no RBAC writes, bind, escalate or impersonate permission. Exact role names alone are not an escalation boundary.

Adoption contracts set `authorization.requireExisting=true`: the executor verifies the artifact, reads each exact object's resourceVersion and sends it as the SSA precondition. Missing objects and concurrent changes fail closed; adoption never silently recreates a deleted object. Ordinary release contracts without this flag retain creation behavior. One-shot Jobs are platform-owned and excluded from replay, and protected storage objects are excluded from force-conflict requests.
