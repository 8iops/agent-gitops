# Agent GitOps repository

- Use signed commits and pull requests for every desired-state change.
- Never commit credentials or decrypted SOPS material.
- Pin images and OCI/Helm artifacts by digest.
- The production root is `clusters/re8ch`.
- Keep product runtime Deployments excluded when their authority is `product-publisher` or `control-plane-direct`.
- Local Flux writers are permanently retired and forbidden. Never create, restore, scale, restart, repair, proxy or grant RBAC to Source, Kustomize, Helm, Notification, image automation, compatibility or domain Flux controllers.
- Retained Flux CRDs and manifests are historical/migration inputs only. GitHub webhooks/Actions plus the bounded cloud SSA executor are the sole delivery path, including emergency recovery.

- Before using RE8CH self-service or platform tools, read [docs/RE8CH-TOOLS.md](docs/RE8CH-TOOLS.md) and discover the current authenticated catalog.

## Shared developer context

- This repository is the desired-state authority for its own domain. The
  [service-backend developer-context declaration](https://github.com/re8ch/service-backend/blob/main/workspace/developer-context.yaml)
  supplies cross-repository navigation only and never overrides this file.
- Start every change from current `origin/main` in a task-specific `codex/*`
  worktree. Keep the base checkout clean; preserve dirty work before cleanup.
- A Codespace is an ephemeral developer machine, not a reconciliation
  controller. GitHub Actions and runtime read-back remain delivery evidence.
- Wiki, Projects and Gists are projections or task evidence. Stable context and
  desired state must be reviewed in Git; never place credentials in them.
- Public evidence follows the [shared privacy contract](https://github.com/re8ch/service-backend/blob/main/contracts/public-evidence-privacy/README.md).
  Public surfaces contain sanitized claims and commitments, never raw personal
  mappings, topology, telemetry, exact event timing or commitment nonces.
- Every change pull request must close an Issue. Every change Issue must belong
  to exactly one requirement Project declared in `governance/context.json`;
  use the `Others` Project when no narrower context applies.
- Keep permissions, dependencies, Code Quality and Dependabot configuration as
  static reviewed context. Put changing observations and investigation evidence
  in Discussions or the Observability Wiki, not in desired-state files.
- Run the validation suite once for each pull-request head. Do not repeat the
  same render, test or build after merging an already validated head.
