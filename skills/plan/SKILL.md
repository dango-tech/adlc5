---
name: adlc5-plan
description: ADLC5 Stage 2 Plan — engineering gates + design discovery/contracts/ops. Invoke via @adlc5-plan.
version: 4.1.0
---

# ADLC5 — Plan

**Stage 2** — engineering craftsmanship + enterprise design.

**Invoke:** `@adlc5-plan for [feature]`

**Persona:** Architect — load [templates/personas/architect.md](../../templates/personas/architect.md) at startup. Memory wall: no product `src/` or `verify/` during Plan.

## Repository context

Run `./scripts/adlc5 repo-index check --workspace .`; refresh when stale. Read the
tracked `.agents/` constitution first, then `.agent-cache/repo-index.json` and only
the module/symbol/dependency/test records relevant to the feature. Source remains
authoritative; generated cache observations never override constitution constraints.

| Step | Craftsmanship | Artifact |
|------|---------------|----------|
| `plan-1-engineering-architecture` | `@clean-architecture-review` | `craftsmanship.architecture_review` |
| `plan-2-engineering-patterns` | `@design-pattern-advisor`, `@pbe-select-patterns` | `craftsmanship.pattern_selection` |
| `plan-3-engineering-algorithms` | `@algorithm-advisor` (if scale NFRs) | `craftsmanship.algorithm_review` |
| `plan-4-design-discovery` | — | `design/1a-discovery.md` |
| `plan-5-design-contracts` | — | `design/1b-contracts.md` |
| `plan-6-design-operations` | Threat model (STRIDE) | `design/1c-operations.md` |
| `plan-7-design-critique` | `@adlc5-design-critic` | `design/design-critique.md` |

Phase docs: [phases/](phases/)

## Research

At `plan-3-engineering-algorithms`, offer `@autoresearch` campaign via AskQuestion when algorithm choice is uncertain.

Before selecting a library/framework version, API, protocol, provider capability,
security practice, or compatibility boundary, recheck an official primary source.
Record `last_verified`, stability status, and source URLs in the design artifact;
stale information is a blocker, not an assumption. Follow
[current-information.md](../../core/guides/current-information.md).

## Design critique (content gate)

At `plan-7-design-critique`, check `state.clarity.score` and `state.scale_nfrs.applicable` first — this is the "decide-late / minimum sufficient profile" SOUL guard applied to Plan's own overhead, not just to model/execution routing:

| Condition | Action |
|-----------|--------|
| `clarity.score ≥ 90` AND `scale_nfrs.applicable` is false/absent | **Skip the subagent spawn.** Write `design/design-critique.md` yourself: one line citing the clarity score and "no scale NFRs" as the skip rationale, `critique_severity: none`. No reasoning-tier round-trip for work that's already unambiguous and low-risk. |
| Otherwise | Spawn `@adlc5-design-critic` (read-only, reasoning tier) over `spec-handoff.md` + `design/1a|1b|1c`, as before. |

Either path writes `design/design-critique.md` with a `critique_severity: none | minor | blocking` verdict — `./scripts/adlc5 gate` reads it at `plan-complete` the same way regardless of which path wrote it:

| Verdict | Gate result | Action |
|---------|-------------|--------|
| `none` | pass | Proceed to Tasks |
| `minor` | warn | HITL: AskQuestion proceed/rework; autonomous: log findings, proceed |
| `blocking` | fail | Rework the cited design substep(s); re-run critic |
| missing | HITL warn / autonomous fail | Run the critic |

## Gate

```bash
./scripts/adlc5 gate --feature "{feature}" --gate plan-complete
./scripts/memory/compact-stage.sh --feature "{feature}" --stage plan
```

## State transition

On pass: `stage_status.plan`: `completed`, `current_stage`: `tasks`, `current_step`: `tasks-1-stories`

## Knowledge

Craftsmanship skills pull OKF cards on demand (≤3) via `./scripts/adlc5 patterns lookup` — cite pattern **ids** in design docs; do not dump catalog or KB essays into Plan chat.

Load KB slices only when a skill step requires depth — [03-clean-architecture.md](../../shared/docs/knowledge-base/03-clean-architecture.md), [04-design-patterns.md](../../shared/docs/knowledge-base/04-design-patterns.md).
