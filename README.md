# RE8CH Agent GitOps

<!-- gitops-status:start -->
[![Reconcile](https://github.com/8iops/agent-gitops/actions/workflows/agent-runtime-reconcile.yml/badge.svg?branch=main)](https://github.com/8iops/agent-gitops/actions/workflows/agent-runtime-reconcile.yml?query=branch%3Amain)
[![Pull request validation](https://github.com/8iops/agent-gitops/actions/workflows/validate.yml/badge.svg?event=pull_request)](https://github.com/8iops/agent-gitops/actions/workflows/validate.yml?query=event%3Apull_request)

Pull-request validation runs once for each PR head. Reconcile reports the
declared release scope, accepted digest, SSA result and separate runtime
observation. Changing evidence belongs in
[Discussions](https://github.com/8iops/agent-gitops/discussions), the
[Observability Wiki](https://github.com/8iops/agent-gitops/wiki/Observability)
or the observability backend.
<!-- gitops-status:end -->

This repository stores reviewed Agent-domain desired state, signed immutable
artifact references and release contracts. Product repositories own source and
build artifacts. Kubernetes owns live state.

Local Flux writers are permanently retired and forbidden. GitHub webhooks and
Actions select reviewed artifacts; the bounded cloud SSA executor is the sole
runtime writer and recovery path.

## Collaboration model

```text
Project → parent Issue → Issue → branch/worktree → signed commits → PR
        → one validation run → merge → runtime evidence → Project status
```

- Projects own requirement domains.
- Parent Issues express outcomes and historical phases.
- One Issue, branch, worktree and PR form one review unit.
- Project fields expose type, status, lifecycle and dates.
- Static permissions, dependencies and release contracts remain in Git.
- Runtime output, investigations and operational stories live in Discussion,
  Wiki or observability.

Use [the Project context template](.github/PROJECT_CONTEXT_TEMPLATE.md) and the
[repository context model](docs/CONTEXT-MODEL.md). Requirement Projects are
declared in [`governance/context.json`](governance/context.json); `Others`
holds context whose ownership is still unresolved.

## Repository map

- `clusters/re8ch`: production Agent desired-state root
- `contracts`: reviewed release and ownership contracts
- `operations/releases`: deterministic compilation and bounded SSA execution
- `operations/cube-recovery`: reviewed recovery inputs
- `governance`: Rulesets, Projects and context-completeness declarations
- `docs`: durable architecture and operating contracts
- `tests`: contract and executor verification

The `static-release` workflow publishes one signed artifact for a reviewed
revision and reuses its digest for replay. SSA execution and runtime observation
remain distinct evidence. Restricted configuration stays encrypted in signed
artifacts and is decrypted only inside the protected executor boundary.

See [`AGENTS.md`](AGENTS.md) before changing desired state and
[`docs/RE8CH-TOOLS.md`](docs/RE8CH-TOOLS.md) before using platform tools.
