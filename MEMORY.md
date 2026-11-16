# Local agent context

- Read `AGENTS.md` first; it is authoritative.
- Reconcile delivery is GitHub Actions OIDC to the bounded cloud SSA executor.
  Local Flux is retired and is never a recovery path.
- Use `docs/GITHUB_OPS_RECONCILE_DEBUGGING.md` for incidents. In particular,
  `state-read-failed` is an exact accepted-state read failure, not evidence that
  a sibling signature or apply job failed.
- Keep secrets and tokens out of Git and logs. Use signed commits and PRs.
