# RE8CH Agent GitOps

<!-- gitops-status:start -->
[![Reconcile](https://github.com/8iops/agent-gitops/actions/workflows/agent-runtime-reconcile.yml/badge.svg?branch=main)](https://github.com/8iops/agent-gitops/actions/workflows/agent-runtime-reconcile.yml?query=branch%3Amain)
[![Pull request validation](https://github.com/8iops/agent-gitops/actions/workflows/validate.yml/badge.svg?event=pull_request)](https://github.com/8iops/agent-gitops/actions/workflows/validate.yml?query=event%3Apull_request)

A badge reports its latest declared workflow scope, not whole-domain health.
Inspect accepted-artifact, SSA and independent observation evidence separately.
<!-- gitops-status:end -->

This repository is the desired-state authority for RE8CH Agent, ToolHive and
agent-runtime guardrails. Product source and release artifacts remain in their
own repositories.

## Requirement context

Every change closes an Issue in an allowed requirement Project. Use
[Others](https://github.com/orgs/8iops/projects/5) only when no narrower Project
applies. Cross-organization references use `owner/repository#number` or full
URLs. See [`docs/CONTEXT-MODEL.md`](docs/CONTEXT-MODEL.md).

## Authority

- `clusters/re8ch` is the production root.
- GitHub Actions and the bounded cloud SSA executor are the only delivery path.
- Local Flux writers are permanently retired and forbidden, including recovery.
- Product-publisher and control-plane-direct workloads remain outside this
  repository's runtime ownership.
- Secret values, personal mappings, topology and raw runtime evidence do not
  belong in Git or another public collaboration surface.

## Delivery

Reviewed changes compile deterministic, signed artifacts. `publish` creates a
new artifact; `reconcile` verifies and replays an accepted digest without
rebuilding it. Missing objects, concurrent changes, undeclared inventory and
unauthorized field ownership fail closed.

Runtime contracts cannot write RBAC, bind, escalate or impersonate. Bootstrap,
credentials, one-shot Jobs and protected storage stay outside replay ownership.
An SSA result proves execution, not service health; read-only observation is a
separate result and never invents rollback authority.

## Evidence and current contracts

Public evidence follows the shared
[privacy contract](https://github.com/re8ch/service-backend/blob/main/contracts/public-evidence-privacy/README.md).
Only coarse signed claims and randomized commitments are public. Restricted
observations belong in the private
[Agent GitOps Observations Project](https://github.com/orgs/8iops/projects/2)
or an approved evidence system.

- [Reconcile boundary](docs/RECONCILE-BOUNDARY.md)
- [Stalwart self-service](operations/releases/STALWART-SELF-SERVICE.md)
- [LiteLLM authority](operations/releases/LITELLM-AUTHORITY.md)
- [Model gateway agent keys](docs/MODEL-GATEWAY-AGENT-KEYS.md)
- [Cube recovery authority](operations/cube-recovery/README.md)
- [Cross-organization context](docs/CROSS-ORG-CONTEXT.md)
- [Dynamic tools](docs/RE8CH-TOOLS.md)
