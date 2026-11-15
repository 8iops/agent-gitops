# Agent reconcile boundary

The scheduled Agent reconcile is a control-plane liveness check, not a replay of
every application object ever compiled by the repository.

```text
reviewed contract + signed digest
              |
              v
scheduled core scope ----> bounded SSA replay ----> Kubernetes read-back

generated domain snapshot --(explicit release_id only)--> bounded SSA replay
```

## Scheduled scope

`operations/releases/scheduled-reconcile.yaml` is the reviewed allowlist for the
daily workflow and its badge. It contains stable Agent control-plane authorities.
Adding a release changes the meaning and runtime of the badge and therefore
requires review.

Generated `agent-runtime-domain-*` releases remain valid signed migration and
recovery artifacts, but product object churn does not automatically enqueue them
in the daily matrix. Operators can still target any trusted contract with the
workflow's exact `release_id` input.

## Authority boundaries

- Git holds reviewed contracts, exact authorization and immutable digests.
- GitHub Actions verifies and replays one accepted artifact.
- Kubernetes is runtime authority and supplies health read-back.
- Secret brokers and bootstrap procedures create credentials and first-instance
  seed objects; the replay workflow does not become a credential orchestrator.

This first reduction intentionally leaves accepted-state compatibility in place.
Removing legacy blocked and history fields is a separate schema migration so a
scope change cannot silently alter rollback or recovery semantics.

## Trade-offs

The badge becomes narrower and more honest, but generated domain drift no longer
surfaces as a red daily Agent badge. That drift must be reported by validation or
an explicit observation workflow. Revisit the allowlist only when a release is
stable enough to be a control-plane dependency rather than an application
snapshot.
