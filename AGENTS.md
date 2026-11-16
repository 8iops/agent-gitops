# Agent GitOps repository

This repository owns reviewed Agent-domain desired state. The production root
is `clusters/re8ch`; product publishers retain their declared runtime authority.

Local Flux writers are permanently retired and forbidden. GitHub webhooks and
Actions plus the bounded cloud SSA executor form the sole delivery and recovery
path.

## Start work

1. Read `docs/RE8CH-TOOLS.md` for current authenticated platform capabilities.
2. Treat `/Volumes/A1/agent-gitops` as the local read-only anchor.
3. Fetch `origin/main` and create one task-specific `codex/*` worktree.
4. Connect the worktree to one delivery Issue and one parent outcome Issue.
5. Keep credentials and decrypted SOPS material in approved secret systems.

## Rich-context delivery

```text
Project → parent Issue → Issue → branch/worktree → commits → PR
        → validation → runtime evidence → Project status
```

- Every change PR closes an Issue.
- Every change Issue belongs to exactly one Project declared in
  `governance/context.json`; `Others` represents unresolved ownership.
- Parent Issues and Milestones express outcomes, phases and historical time.
- Project items carry type, lifecycle, status, relevant dates and local risk.
- Signed commits describe the smallest coherent desired-state transition.
- Validation runs once for each PR head. A changed head starts a new run.
- Immutable artifacts are built once per source revision and build configuration,
  then reused through verification and delivery.

Use `.github/PROJECT_CONTEXT_TEMPLATE.md` for new Projects and reconstruction.

## Code and context

- Prefer existing GitHub and platform primitives and the smallest implementation.
- Keep comments for non-obvious invariants, security boundaries and external
  contracts. Names, types and tests explain ordinary control flow.
- Remove obsolete code, duplicate adapters and stale commentary while changing
  their owning path.
- Keep permissions, dependencies, Code Quality, Dependabot and release authority
  as static reviewed context.
- Put Kubernetes output, incident timelines, experiments and migration stories
  in Discussions, Wiki or observability; Issues link the evidence to outcomes.
- Read back GitHub checks and actual runtime state before completing Project work.

Generated cross-repository context provides navigation. This file and reviewed
repository contracts define Agent GitOps authority.
