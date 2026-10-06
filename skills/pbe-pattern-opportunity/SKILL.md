---
name: pbe-pattern-opportunity
description: >-
  Identify pattern opportunities using Rule of Three and iteration scanning.
  Use during Specify or Plan to spot recurrence before cataloging. Invoke
  with @pbe-pattern-opportunity.
---

# S4 — PBE Pattern Opportunity

**ADLC5 stage:** Spec / Engineer  
**Skill ID:** S4  
**Knowledge base:** [Part I — Patterns-Based Engineering §I.4](../../shared/docs/knowledge-base/01-pbe.md)  
**Rules:** R0 `pbe-core-values.mdc`  
**Playbook:** Part I §I.2 (Rule of Three), §I.4 (Identification), §I.7 (antipatterns)

Do not dump OKF catalog into this skill — cite candidate ids; load ≤1 related `pbe/*` card only if needed (`./scripts/adlc5 patterns lookup --group pbe`).

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Scan for recurring problem-solution pairs that may become org pattern assets. S4 applies Rule of Three before any catalog investment—identification without premature specification.

## When to invoke

- End of iteration retrospective or feature completion
- Scanning codebase/path for repeated problem-solution pairs
- User asks "should this become a pattern?"
- Start of codify workflow: S4 → S8 → S7 → S10 → S9

**Do not invoke for:** writing full pattern specs (S7) or ROI analysis alone (S8).

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Scan scope, sources of evidence |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Recurrence, Rule of Three |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Candidates, actions, S8 routing |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Scan scope** — Path, repo, or recent PRs; note domain-agnostic problem statements.
2. **List recurrences** — Same forces + same solution shape in distinct contexts.
3. **Rule of Three** — Candidate requires **three unique situations**; document evidence (links, tickets, paths).
4. **Classify opportunity** — Architectural vs design vs idiom; large-scope first (R1).
5. **Exemplar pointers** — Best reference implementations for S10 analysis.
6. **Antipattern guard** — Reject "patterns everywhere"; one opportunity per real recurrence.
7. **Next gate** — If candidate, route to `@pbe-determine-business-impact` (S8) before catalog.

## Rule of Three

| Count | Status |
|-------|--------|
| 1 occurrence | Observation only |
| 2 occurrences | Watch — not yet catalog-worthy |
| 3+ unique contexts | Candidate for S8 ROI gate |

**Unique context** = different team, product, bounded context, or integration—not copy-paste of same module.

## Opportunity classification

| Scope | Examples | Typical skill path |
|-------|----------|-------------------|
| Architectural | Ports/adapters, event outbox | S2 + S7 |
| Design | Strategy family, Factory for plugins | S3 + S7 |
| Idiom | Retry wrapper, idempotency key | S7 + S9 rule/hook |

## Integration with ADLC5

```
Specify/Plan S4 → Catalog S8 → S10 → S7 → S9
```

- S4 runs during iteration—not deferred to "harvest at end" (I.5 piecemeal).
- Failed S8 → use GoF ad hoc via S3/S5; no `shared/docs/patterns/` entry.

## Output format

```markdown
## Pattern Opportunity Scan — [scope]

### Candidates
| ID | Problem (context-free) | Occurrences | Evidence | Scope |
|----|------------------------|-------------|----------|-------|

### Rule of Three status
| Candidate | Count | Unique contexts | Meets Rule of Three? |
|-----------|-------|-----------------|----------------------|

### Recommended actions
| Candidate | Action |
|-----------|--------|
| … | Proceed to S8 | Defer — need more evidence | Use GoF ad hoc |

### Exemplars for S10
- …
```

Write candidates to `docs/patterns/_candidates/` only when user requests persistence.

Reference: playbook Part I §I.2 (Rule of Three), §I.4 (Identification), §I.7 (antipatterns).

## Antipatterns

| Antipattern | Mitigation |
|-------------|------------|
| Patterns everywhere | Business impact gate (S8) |
| Perfect Pattern | Piecemeal S9 after S7 |
| Get 'em next time | Scan each iteration (S4) |
| Waterfall pattern use | Identify during current project |

## Handoffs

| Outcome | Next skill |
|---------|------------|
| Rule of Three met | S8 `@pbe-determine-business-impact` |
| Need structure from code | S10 `@pbe-exemplar-analysis` |
| Consumption only | S3/S5 GoF ad hoc |

## Scan heuristics

| Signal | Likely opportunity |
|--------|-------------------|
| Same review comment 3+ times | Idiom or rule candidate |
| Copy-pasted adapter blocks | Integration pattern |
| Parallel package structure | Architectural pattern |
| Repeated `// TODO: generalize` | Deferred pattern asset |

Capture **evidence links** at scan time—retro memory fades before S8.

## Iteration timing

Run S4 at:

- Sprint retrospective
- Feature epic completion
- Major refactor merge
- Quarterly catalog hygiene review

Piecemeal creation (I.5): note opportunities **during** the project, not post-hoc harvest only.
