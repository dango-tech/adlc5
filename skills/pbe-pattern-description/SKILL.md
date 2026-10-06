---
name: pbe-pattern-description
description: >-
  Write org pattern specification — context, problem, forces, solution,
  consequences, variability points. Use at Catalog stage after S8 ROI gate.
  Invoke with @pbe-pattern-description.
---

# S7 — PBE Pattern Description

**ADLC5 stage:** Catalog (Production)  
**Skill ID:** S7  
**Knowledge base:** [Part I §I.2 Specification](../../shared/docs/knowledge-base/01-pbe.md)  
**Rules:** R0 `pbe-core-values.mdc`  
**Playbook:** Part I §I.2 (spec vs implementation), Part IX (catalog template)

Author **one** OKF concept at a time; update indexes — do not load the full catalog into context while writing. See [patterns/README.md](../../shared/docs/patterns/README.md) progressive disclosure.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Author consumable org pattern specifications separating **specification** from **implementation**. S7 runs only after S8 ROI approval—patterns are engineered assets with metadata, variability points, and lifecycle.

## When to invoke

- S8 ROI gate passed; candidate promoted from `docs/patterns/_candidates/`
- Authoring or revising an OKF concept under `shared/docs/patterns/` (see [patterns/README.md](../../shared/docs/patterns/README.md))
- Pattern version bump after feedback (patterns are alive)

**Prerequisites:** Rule of Three evidence (S4), ROI approval (S8), exemplar analysis (S10) recommended.

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | S8 gate, S10 input, candidate ID |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Context, forces, structure |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Write `docs/patterns/<id>.md` |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Confirm gate** — S8 approved; candidate ID and evidence linked.
2. **Context** — When does this pattern apply? Boundaries and preconditions.
3. **Problem & forces** — Recurring tension; quality attributes at stake.
4. **Solution** — Structure, roles, collaborations; variability points explicit.
5. **Consequences** — Trade-offs, liabilities, related patterns.
6. **Metadata** — YAML frontmatter per playbook Part IX template:
   - `id`, `name`, `version`, `status`, `requirements_tags`, `related_patterns`
   - `implementation`: skill | rule-only | hook
   - `complexity_notes` if algorithmic
7. **Consumability** — Findable name, one-page summary, link to exemplar(s).
8. **Handoff** — If automation needed, route to S9 (piecemeal skill/rule).

## Metadata fields (Part IX)

| Field | Purpose |
|-------|---------|
| `id` | Stable kebab-case identifier |
| `name` | Human-readable title |
| `version` | Semver; bump on material spec change |
| `status` | candidate \| approved \| deprecated |
| `requirements_tags` | For S5 catalog search |
| `related_patterns` | Density combinations |
| `implementation` | skill \| rule-only \| hook |
| `roi_notes` | Summary from S8 |
| `complexity_notes` | O(·) if applicable |

## Integration with ADLC5

```
S4 → S8 (approve) → S10 → S7 → S9 → consumption via S5/S6
```

- Specification lives as an OKF concept in `shared/docs/patterns/` (update group + root `index.md` and `log.md`); implementation in skills/rules/hooks (S9).
- Do not copy exemplar code into spec—structure and pointers only.

## Output format

Write to `docs/patterns/<pattern-id>.md`:

```markdown
---
id: pattern-id
name: Human Name
version: 1.0.0
status: candidate | approved
requirements_tags: [...]
related_patterns: [...]
implementation: skill | rule-only | hook
roi_notes: "From S8"
complexity_notes: "Optional O(·)"
---

# [Name]

## Context
…

## Problem
…

## Forces
…

## Solution
…

## Variability points
| Point | Options |
|-------|---------|

## Consequences
…

## Exemplars
- …

## Related
…
```

Reference: playbook Part I §I.2 (spec vs implementation), Part IX (catalog template).

## Quality gates

- [ ] S8 approval referenced in `roi_notes`
- [ ] Variability points table complete
- [ ] No exemplar code paste—pointers only
- [ ] Related patterns cross-linked
- [ ] Implementation type declared for S9

## Handoffs

| Next | When |
|------|------|
| S9 | `implementation: skill` or rule/hook needed |
| S5 | Pattern approved—available for Engineer consumption |
| Version bump | Feedback from S6 or production use |
