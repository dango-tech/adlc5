---
name: pbe-exemplar-analysis
description: >-
  Derive pattern structure from reference code — roles, collaborations,
  variability points. Use at Catalog stage to feed S7 specs. Invoke with
  @pbe-exemplar-analysis.
---

# S10 — PBE Exemplar Analysis

**ADLC5 stage:** Catalog (Production — discovery input)  
**Skill ID:** S10  
**Knowledge base:** [Part I §I.2 Exemplar + §I.4 Production](../../shared/docs/knowledge-base/01-pbe.md)  
**Rules:** R0 `pbe-core-values.mdc`  
**Playbook:** Part I §I.2 (exemplar, specification), §I.4 (Production)

Work from exemplar code + the candidate/spec under edit — do not dump the OKF catalog into context.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Reverse-engineer pattern structure from reference implementations. Patterns are **discovered** from exemplars—not invented in vacuum. S10 feeds S7 specification with roles, collaborations, and variability points grounded in real code.

## When to invoke

- Before or during S7 pattern description authoring
- S4 candidate has reference implementation(s) to generalize
- Reverse-engineering legacy via pattern vocabulary (consumption guideline)
- Patterns are **discovered** from exemplars, not invented in vacuum

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Exemplar paths, S4 evidence |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Roles, collaborations, variability |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | S7-ready structure |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Select exemplar(s)** — Best reference code paths from S4; prefer clearest, tested instance.
2. **Abstract problem** — Strip domain specifics; state context-free problem and forces.
3. **Identify roles** — Name participants (e.g., Strategy, Context, ConcreteStrategy analogs).
4. **Map collaborations** — Who calls whom; dependency direction (align with R2 if architectural).
5. **Extract variability points** — What changes between the three Rule of Three contexts.
6. **Name pattern** — Catalog id + GoF alignment if applicable; note confusion pairs (Part IV).
7. **Gap analysis** — What exemplar does not cover; risks if over-generalized.
8. **Feed S7** — Output sections map directly to pattern spec template.

## Exemplar selection criteria

| Criterion | Prefer |
|-----------|--------|
| Clarity | Shortest path showing full role set |
| Tests | Exemplar has automated tests |
| Quality | Passes S2/S1 at reasonable bar |
| Diversity | Three contexts for variability comparison |

## Integration with ADLC5

```
S4 (pointers) → S10 → S7 → S9
         ↑
    S8 gate (parallel or before S7)
```

S10 can run before S8 to inform ROI realism—exemplar cost visible early.

## Output format

```markdown
## Exemplar Analysis — [candidate / path]

### Exemplars reviewed
| Path | Quality | Notes |
|------|---------|-------|

### Problem (abstracted)
…

### Forces
…

### Structure
| Role | Exemplar type/module | Responsibility |
|------|---------------------|----------------|

### Collaboration diagram
[mermaid or bullet flow]

### Variability points
| Point | Exemplar A | Exemplar B | Exemplar C |
|-------|------------|------------|------------|

### Proposed pattern name / id
…

### GoF alignment
…

### Gaps & cautions
…

### Ready for S7
- [ ] Yes — sufficient abstraction
- [ ] No — need additional exemplar
```

Do not copy exemplar code into catalog; document structure and pointers only.

Reference: playbook Part I §I.2 (exemplar, specification), §I.4 (Production), Part I consumption — use pattern definitions to understand legacy.

## Quality gates

- [ ] ≥1 exemplar analyzed; 3 for full variability table when available
- [ ] Roles map to modules/types—not line numbers only
- [ ] Problem statement domain-agnostic
- [ ] GoF alignment or explicit "novel org pattern"
- [ ] Gaps documented honestly

## Handoffs

| Outcome | Next |
|---------|------|
| Ready for S7 | `@pbe-pattern-description` |
| Need more exemplars | Back to S4 scan |
| Not generalizable | S8 reject path |

## Anti-patterns

- Copy-pasting exemplar into S7 spec
- Naming pattern after one team's domain noun
- Ignoring dependency direction (R2) in collaboration map
- Over-generalizing from buggy exemplar
