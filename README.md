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
