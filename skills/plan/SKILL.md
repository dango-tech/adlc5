---
name: adlc5-plan
description: ADLC5 Stage 2 Plan — engineering gates + design discovery/contracts/ops. Invoke via @adlc5-plan.
version: 4.1.0
---

# ADLC5 — Plan

**Stage 2** — engineering craftsmanship + enterprise design.

**Invoke:** `@adlc5-plan for [feature]`

**Persona:** Architect — load [templates/personas/architect.md](../../templates/personas/architect.md) at startup. Inspect existing source read-only to understand the flow; do not edit product code
or use implementation verification reports as design authority.

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

## Proportionate planning

For `standard`, write one `design/plan.md`: existing flow to reuse, affected files
and boundaries, intended behavior, compatibility/risk decisions, and checks.
Run only `plan-4-design-discovery`; pull craftsmanship references only to resolve
an actual design question. For `tiny`, keep these decisions in `change.md` during
Specify. Do not generate the full design tree or spawn every persona.

For `high_risk` or `full`, keep the detailed design ladder and independent
`@adlc5-design-critic`. Clarity score and absent scale NFRs do not establish low
risk and cannot waive required critique. Record `risk.json` before progression;
uncertain/trust-boundary/data-safety work requires the high-risk route.

Critique `blocking` prevents progression; `minor` requires recorded disposition.

## Gate

```bash
./scripts/adlc5 gate --feature "{feature}" --gate plan-complete
./scripts/memory/compact-stage.sh --feature "{feature}" --stage plan
```

## State transition

On pass: `./scripts/adlc5 transition tasks-1-stories --feature "{feature}"`.
The kernel validates the selected route and writes progress; never patch it via `state set`.

## Knowledge

Craftsmanship skills pull OKF cards on demand (≤3) via `./scripts/adlc5 patterns lookup` — cite pattern **ids** in design docs; do not dump catalog or KB essays into Plan chat.

Load KB slices only when a skill step requires depth — [03-clean-architecture.md](../../shared/docs/knowledge-base/03-clean-architecture.md), [04-design-patterns.md](../../shared/docs/knowledge-base/04-design-patterns.md).
