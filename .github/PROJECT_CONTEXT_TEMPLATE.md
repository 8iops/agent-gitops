# Project context template

Use one Project for a product, runtime capability or governance domain. Local
schemas may extend this template while preserving semantic completeness.

## Project description

```markdown
## Outcome
<Durable capability or governance result>

## Scope
- Repositories: <owner/repository>
- Runtime surfaces: <services or namespaces>
- Evidence: <Checks, Deployments, Discussion, Wiki or observability>

## Context contract
Every PR closes an Issue. Every Issue belongs to this Project. Parent Issues and
Milestones express outcomes and phases. Project fields record status and time.
```

## Hierarchy

```text
Project
├── parent Feature: outcome or historical phase
│   ├── Feature/Bug/Task: one reviewable concern
│   └── Feature/Bug/Task: one reviewable concern
└── parent Feature: next outcome or phase
```

Historical reconstruction groups PRs by meaningful capability or phase. Each
PR appears in one historical Feature. `Others` receives evidence whose ownership
is unresolved and is revisited when new context arrives.

## Fields

| Field | Meaning |
| --- | --- |
| Status | Todo, In Progress, Done |
| Type | Feature, Bug, Task |
| Lifecycle | Backlog, Ready, In Progress, Blocked, Done, Cancelled, Historical |
| Work Type | Feature, Bug, Task, Governance, Dependency, Documentation, Migration, Historical |
| Context Status | Draft, Ready, Complete, Historical |
| Priority / Risk | Local priority and operational exposure |
| Start Date | First meaningful work or historical PR date |
| Target Date | Planned completion |
| Completed Date | Verified completion or final historical date |

## Views

1. `List`: table with Title, Status, Repository, Type, Parent issue,
   Sub-issues progress, Lifecycle, Work Type, Context Status and dates.
2. `Status`: board grouped by Status with context fields visible.
3. `Timeline`: roadmap using Start Date and Completed Date; Target Date carries
   unfinished work.

## Issue body

```markdown
## Outcome
<Observable result>

## Context
- Parent Issue: #
- Project: <link>
- Milestone: <name>
- Branch/worktree: <name>

## Acceptance
- [ ] Static contract or code verification
- [ ] Runtime verification where applicable
- [ ] Evidence linked below

## Evidence
<Checks, Deployment, Discussion, Wiki or observability links>
```

## Delivery

- One Issue, concern, branch and worktree form one review unit.
- Signed commits describe coherent desired-state transitions.
- The PR closes the Issue and links immutable build and runtime evidence.
- Each validation class runs once for an unchanged revision.
- Source comments explain invariants; Issues and knowledge surfaces carry stories.
- Project status changes after the corresponding evidence is verified.
