---
name: adlc5-tasks
description: ADLC5 Stage 3 Tasks — user stories, parallel batches, TDD code specs. Invoke via @adlc5-tasks.
version: 5.3.1
---

# ADLC5 — Tasks

**Stage 3** — decompose work and write TDD-ready code specs.

Map every requirement and decision to its affected stories in readiness
`delivery.traceability`, with acceptance IDs matching each code spec. Unknown
dependencies block implementation. On intent changes, run `readiness impact`,
reassess risk and applicability, preserve old anchors and request an attributable
acceptance revision through the existing anchor workflow. Do not silently relock.

**Invoke:** `@adlc5-tasks for [feature]`

## Persona handoff

| Step | Persona | Gate |
|------|---------|------|
| `tasks-1-stories` | Analyst | `tasks-1-stories-complete` |
| `tasks-2-code-spec` | Architect | `tasks-2-code-spec-complete` |

Load [analyst.md](../../templates/personas/analyst.md) or [architect.md](../../templates/personas/architect.md) per step. Update `persona.active` in state on handoff.

## Step ladder

| Step | Purpose | Artifact |
|------|---------|----------|
| `tasks-1-stories` | Story decomposition + conflict analysis | `state.tasks.stories`, `tasks/stories.json` |
| `tasks-2-code-spec` | Tests listed before code; frontmatter linted (`spec-lint.py`) | `tasks/code-spec/{story-id}.md` |

## Scripts

Read the current `requirements-readiness.json` when decomposing the handoff.
Preserve its reviewed decisions and acceptance scenarios in stories and code specs;
changed intent requires reassessment before progression.

Populate each story's `acceptance` entries (unique ID, owner, file/command evidence)
in canonical `state.tasks.stories` while authoring `tasks/stories.json`. Criteria
only in code-spec prose/frontmatter do not populate state. Use `state set` for
Tasks metadata before locking; preserve story statuses. Every story needs criteria,
and an empty anchor lock fails without creating a manifest or Git trust ref.

For volatile versions, APIs, protocols, provider capabilities, or security
guidance carried into stories/code specs, recheck official primary sources and
follow [current-information.md](../../core/guides/current-information.md).

After story changes:

```bash
./scripts/tasks/render-board.sh --feature "{feature}"
```

After writing each code spec's frontmatter:

```bash
./scripts/tasks/spec-lint.py --feature "{feature}" --story-id "{id}"
```

Before implement subagent:

```bash
./scripts/adlc5 pack --feature "{feature}" --story-id "{id}"
```

Code specs and context packs must cite the repository-index snapshot and the selected
`.agent-cache/` records used to choose affected files and tests. Do not embed the
entire cache in a story pack.

## Gate

```bash
./scripts/adlc5 gate --feature "{feature}" --gate tasks-1-stories-complete   # after stories
./scripts/adlc5 gate --feature "{feature}" --gate tasks-2-code-spec-complete # after code specs
./scripts/adlc5 gate --feature "{feature}" --gate tasks-complete             # aggregate
./scripts/adlc5 anchors lock --feature "{feature}"                           # freeze before Implement
./scripts/memory/compact-stage.sh --feature "{feature}" --stage tasks
```

Do not transition to Implement unless `anchors lock` passes. A `high_risk` profile
(or `autopilot.require_anchors: true`) needs at least one `evidence.type: file`
criterion, or the lock fails. It atomically applies
file digests to schema-validated state and seals every acceptance definition,
including command text, in `.adlc5/{feature}/acceptance-lock.json`. A Git-backed
worktree-tamper reference is retained at
`refs/adlc5/anchors/{feature}`; Verify compares both state and the local manifest
to that ref. Approved relocking updates all three together. This local ref is not
an independent security boundary, is not transported by normal Git remotes, and
can be moved by an actor with Git-write access; require external human signing
when that actor is in the threat model.

## State transition

On pass: `./scripts/adlc5 transition implement-1-build --feature "{feature}"`.
Never assert progression through `state set`.

## Parallel batches

Store in `state.tasks.parallel_batches`. Use `@build-implementer` per batch (max 4 parallel when policy allows).

`tasks-complete` rejects duplicate/missing dependencies, cycles, dependency batch inversions, and same-batch file overlap through `scripts/tasks/validate-graph.py`.
