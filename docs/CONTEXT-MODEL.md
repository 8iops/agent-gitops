# Repository context model

`agent-gitops` uses GitHub Projects, Issues and pull requests as a small
requirement graph rather than as an approval hierarchy:

```text
Requirement Project -> Issue -> pull request -> one validation run -> merge
```

Issues are free-form. Before an Issue can authorize a change, it must belong to
exactly one requirement Project listed in `governance/context.json`. Use
**Others** when no narrower Project applies. A pull request must close at least
one such Issue by using a closing keyword such as `Closes #171`.

Each requirement Project has a matching `project:*` label. The repository
`GITHUB_TOKEN` cannot read organization ProjectV2 membership, so the pull-request
check validates the unique label without adding a long-lived credential. The
Project remains authoritative; the governance GitHub App performs runtime
read-back and reports any Project/label mismatch as an observation.

No review count is implied by this model. The relationship check establishes
context and traceability; it does not create an artificial approval role for an
agent.

The default-branch Ruleset requires this single check with zero approving
reviews. Signed linear PR merges replace direct pushes, force pushes and branch
deletion. The reviewed declaration is `governance/rulesets/main.json`; applying
the declaration must be followed by an API read-back of the effective Ruleset.

## Static boundary

Git contains durable desired context:

- permissions, authority and ownership;
- dependency and immutable artifact relationships;
- Code Quality expectations and the single validation workflow;
- Dependabot configuration;
- Project identities and the Issue/PR relationship policy.

The validation workflow runs on a pull request head only. Merging the already
validated head does not repeat the same build, render or test suite on `push`.
Release and runtime workflows consume immutable reviewed inputs separately.

## Dynamic boundary

Discussions and the Observability Wiki contain changing observations,
investigation notes and links to external telemetry. Raw telemetry, alerts,
workflow-run snapshots and runtime health are not committed as desired context.

The historical **Agent GitOps Observations** Project is a read-only transition
source. Do not add new observations to it; project durable remediation work into
an Issue and put the changing evidence in Discussions or the Observability Wiki.

Runtime checks remain runtime evidence. This repository does not add a second
dynamic security scanner to pull-request CI. GitHub CodeQL Default Setup is
disabled; ingress secret push protection remains a repository content guard,
not a runtime scan workflow.
