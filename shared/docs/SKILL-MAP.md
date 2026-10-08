# ADLC5 Skill Map

Invoke reference for Specify → Plan → Tasks → Implement and auxiliary skills.

**Lifecycle:** [docs/ADLC5.md](../../docs/ADLC5.md) · `./scripts/install.sh` · [INSTALL.md](INSTALL.md)

**Guides:** [phase-registry.md](../../core/guides/phase-registry.md) · [clarity-scoring.md](../../core/guides/clarity-scoring.md) · [askquestion-convention.md](../../core/guides/askquestion-convention.md)

## Core invokables

| Invoke | Stage | Skill path |
|--------|-------|------------|
| `@adlc5` | All + autopilot | [skills/adlc5](../../skills/adlc5/SKILL.md) |
| `@adlc5-specify` | Specify | [skills/specify](../../skills/specify/SKILL.md) |
| `@adlc5-plan` | Plan | [skills/plan](../../skills/plan/SKILL.md) |
| `@adlc5-tasks` | Tasks | [skills/tasks](../../skills/tasks/SKILL.md) |
| `@adlc5-implement` | Implement | [skills/implement](../../skills/implement/SKILL.md) |

**Plugin setup:** `@adlc5-setup` — [skills/adlc5-setup](../../skills/adlc5-setup/SKILL.md) — host-plugin consumer setup (preflight, missing scaffolding, duplicate classic-install detection); repeat-safe.

**Fifth pillar (cross-cutting):** `@adlc5-soul` — [skills/adlc5-soul](../../skills/adlc5-soul/SKILL.md) — evidence-driven five-guard reasoning for graph-routed work: preserve acceptance, choose the minimum sufficient profile, honor dependencies, require independent evidence, then optimize cost. Rule: [adlc5-soul.md](../rules/portable/adlc5-soul.md).

State: `.adlc5/{feature}/state.json` (schema 3.0) · Memory: `.adlc5/{feature}/memory/INDEX.md` — [working-memory.md](../../core/guides/working-memory.md)

Registry: [core/skill-registry.yaml](../../core/skill-registry.yaml) · Personas: [core/personas.yaml](../../core/personas.yaml)

## Auxiliary skills

Not separate lifecycle stages — wired via `skill-registry.yaml`. Index: [skills/aux/README.md](../../skills/aux/README.md).

| Invoke | Skill | Typical stage |
|--------|-------|---------------|
| `@discover` | [discover](../../skills/discover/SKILL.md) | Specify |
| `@prt` | [prt](../../skills/prt/SKILL.md) | Specify |
| `@clean-architecture-review` | [clean-architecture-review](../../skills/clean-architecture-review/SKILL.md) | Plan |
| `@design-pattern-advisor` | [design-pattern-advisor](../../skills/design-pattern-advisor/SKILL.md) | Plan |
| `@algorithm-advisor` | [algorithm-advisor](../../skills/algorithm-advisor/SKILL.md) | Plan |
| `@adlc5-design-critic` | [adlc5-design-critic](../../skills/adlc5-design-critic/SKILL.md) | Plan gate (`plan-7-design-critique`) + pre-Build |
| `@autoresearch` | [autoresearch](../../skills/autoresearch/SKILL.md) | Plan |
| `@build-implementer` | [build-implementer](../../skills/build-implementer/SKILL.md) | Implement (subagent) |
| `@assure-verifier` | [assure-verifier](../../skills/assure-verifier/SKILL.md) | Implement (subagent) |
| `@adlc5-assure-reworker` | [adlc5-assure-reworker](../../skills/adlc5-assure-reworker/SKILL.md) | Implement (subagent) |
| `@adlc5-tdd` | [adlc5-tdd](../../skills/adlc5-tdd/SKILL.md) | Implement |
| `@craftsmanship-code-review` | [craftsmanship-code-review](../../skills/craftsmanship-code-review/SKILL.md) | Implement |
| `@complexity-review` | [complexity-review](../../skills/complexity-review/SKILL.md) | Implement |
| `@qa` | [qa](../../skills/qa/SKILL.md) | Implement |
| `@pr-reviewer` | [pr-reviewer](../../skills/pr-reviewer/SKILL.md) | Implement |
| `@adlc5-project-wiki` | [project-wiki](../../skills/project-wiki/SKILL.md) | Post `pr-ready` |
| `@infra` | [infra](../../skills/infra/SKILL.md) | Post-Plan IaC authoring/validation (baseline for `@qa`) |
| `@deploy` | [deploy](../../skills/deploy/SKILL.md) | Post-merge, gated by `deploy-ready` (always HITL) |

## Craftsmanship (S1–S10)

| ID | Invoke | Skill |
|----|--------|-------|
| S1 | `@craftsmanship-code-review` | [craftsmanship-code-review](../../skills/craftsmanship-code-review/) |
| S2 | `@clean-architecture-review` | [clean-architecture-review](../../skills/clean-architecture-review/) |
| S3 | `@design-pattern-advisor` | [design-pattern-advisor](../../skills/design-pattern-advisor/) |
| S3b | `@algorithm-advisor` | [algorithm-advisor](../../skills/algorithm-advisor/) |
| S3c | `@complexity-review` | [complexity-review](../../skills/complexity-review/) |
| S4 | `@pbe-pattern-opportunity` | [pbe-pattern-opportunity](../../skills/pbe-pattern-opportunity/) |
| S5 | `@pbe-select-patterns` | [pbe-select-patterns](../../skills/pbe-select-patterns/) |
| S6 | `@pbe-review-with-patterns` | [pbe-review-with-patterns](../../skills/pbe-review-with-patterns/) |
| S7–S10 | Catalog skills | `pbe-determine-business-impact`, `pbe-pattern-description`, `pbe-exemplar-analysis`, `pbe-piecemeal-skill` under `skills/` |

## Project wiki (optional)

Spec: [project-wiki.md](project-wiki.md) · Scripts: `scripts/wiki/`

Repository context is always available before feature SDD: tracked `.agents/`
constitution plus generated `.agent-cache/` intelligence. See
[repository-context.md](../../core/guides/repository-context.md).

## Recommended invoke chain

```
@adlc5 for [feature]
```

Stage-by-stage:

```
@adlc5-specify for [feature]
@adlc5-plan for [feature]
@adlc5-tasks for [feature]
@adlc5-implement for [feature]
```

Upstream (optional): `@discover` → `@prt` before or within Specify.

## Knowledge base

Book summaries (primary reference): [knowledge-base/](knowledge-base/README.md)

| File | Book |
|------|------|
| 01-pbe.md | Patterns-Based Engineering |
| 02-clean-code.md | Clean Code |
| 03-clean-architecture.md | Clean Architecture |
| 04-design-patterns.md | Head First Design Patterns |
| 05-algorithms-clrs.md | CLRS |
| 06-synthesis.md | Cross-book synthesis |

Operational reference: [playbook.md](playbook.md)

## Cursor rules

Installed to `~/.cursor/rules/` from [.cursor/rules/](../../.cursor/rules/) — R0–R5 plus discipline, clean-code, MCP retrieval, **adlc5-interaction** (AskQuestion).

## Model profiles and working memory

| Guide | Purpose |
|-------|---------|
| [model-matrix.md](../../core/guides/model-matrix.md) | Abstract tiers (`reasoning`, `balanced`, `implementation`) |
| [working-memory.md](../../core/guides/working-memory.md) | Feature memory index and context packs |
| [platform-tooling.md](../../core/guides/platform-tooling.md) | Per-host model picker + memory |

Templates: [templates/memory/](../../templates/memory/) · Cursor mapping: [templates/cursor-models.md](../../templates/cursor-models.md)

## Cross-platform

See [CROSS-PLATFORM.md](CROSS-PLATFORM.md) for Cursor, Claude, Codex, OpenCode, Gemini, Hermes Agent, Antigravity invoke syntax.
