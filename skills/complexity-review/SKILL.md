---
name: complexity-review
description: >-
  Hot-path O(·) review and CLRS anti-pattern detection. Use during Implement on
  PRs with scale NFRs or performance-sensitive code. Invoke with
  @complexity-review.
---

# S3c — Complexity Review

**ADLC5 stage:** Implement
**Skill ID:** S3c  
**Knowledge base:** [Part V — CLRS §V.9 anti-patterns](../../shared/docs/knowledge-base/05-algorithms-clrs.md)  
**Rules:** R5 `algorithm-complexity.mdc`  
**Playbook:** Part V §V.1–V.2 (O/Ω/Θ), §V.9 (anti-patterns)

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Verify implemented hot paths match documented O(·) and scale NFRs. S3c is the Implement counterpart to Plan's S3b—catch anti-patterns before merge on performance-sensitive diffs.

## When to invoke

- PR review on search, sort, graph, batch, or aggregation code
- Implement gate when an S3b advisory was issued for the feature
- Suspected O(n²)+ on large `n` or missing complexity documentation
- Companion to `@pr-reviewer` and S1 on performance-critical diffs

**Do not invoke for:** choosing algorithms pre-build (use S3b) or general code smells (S1).

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Diff scope, S3b doc, NFRs |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Hot paths, O(·), anti-patterns |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Verdict, remediation |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Identify hot paths** — Loops, recursive calls, DB/API batch patterns in the diff.
2. **Expected n** — Compare documented NFRs vs actual access patterns in code.
3. **State O(·)** — For each hot path: time and space; cite line ranges.
4. **Check anti-patterns** — Part V §V.9 checklist:
   - Nested loops on large `n` without justification
   - Wrong algorithm (Dijkstra + negative weights, greedy without proof)
   - Hash when ordering/range queries needed
   - Micro-optimizing cold paths while hot path stays quadratic
   - Exponential brute force on large inputs
5. **N+1 / I/O** — Hidden linear multipliers (queries in loops, unbounded fan-out).
6. **Verdict** — Pass if O(·) documented and appropriate; fail with remediation.

## Anti-pattern checklist (V.9)

| ID | Anti-pattern | Detection signal |
|----|--------------|------------------|
| AP1 | O(n²) nested loops | Loop inside loop on same collection |
| AP2 | Wrong graph algo | Negative edges with Dijkstra |
| AP3 | Wrong DS | Hash map for sorted range queries |
| AP4 | Cold-path tuning | Bit tricks while hot path quadratic |
| AP5 | Exponential brute force | Recursive subsets on n > 20 |
| AP6 | N+1 I/O | ORM/query inside loop |

## Integration with ADLC5

```
Plan S3b → Tasks code spec cites O(·) → Implement S3c + S1 + @pr-reviewer
```

- If S3b was N/A, S3c may still run when diff introduces loops on unbounded collections.
- Escalate architectural DS placement issues to S2.

## Output format

```markdown
## Complexity Review — [scope / PR]

**Verdict:** pass | pass-with-notes | fail

### Hot paths
| Path | Location | Stated O(·) | Expected n | Assessment |
|------|----------|-------------|------------|------------|

### Anti-pattern hits
| ID | Issue | Location | Fix |
|----|-------|----------|-----|

### Missing documentation
- …

### Recommendations
1. …
```

If no scale NFRs apply, output: **N/A — sufficient for expected n; no hot-path review required.**

Reference: playbook Part V §V.1–V.2 (O/Ω/Θ), §V.9 (anti-patterns).

## Verdict criteria

| Verdict | Criteria |
|---------|----------|
| **pass** | O(·) appropriate and documented; no AP hits |
| **pass-with-notes** | Minor doc gap; algorithm sound |
| **fail** | AP hit on production hot path or missing justification for quadratic+ |

## Handoffs

| Finding | Route |
|---------|-------|
| Algorithm reselection needed | Back to S3b (Engineer rework) |
| Smell-level loop clarity | S1 |
| Wrong DS in domain layer | S2 |

## Review techniques

| Technique | When to use |
|-----------|-------------|
| Loop nesting count | Nested iteration over same or related collections |
| Aggregate API audit | ORM `include`, GraphQL nested resolvers, N+1 queries |
| Recursion depth | Unbounded recursion on user input |
| Batch size caps | Streams loading entire tables into memory |
| Spec cross-check | Compare code loops to S3b stated O(·) |

Document **observed** complexity even when S3b said N/A—implementation may introduce hot paths anyway.

## Companion review order

Recommended Implement review sequence for performance-sensitive PRs:

1. S3c — complexity and anti-patterns
2. S1 — readability of hot-path code
3. S6 — pattern fit if Strategy/DS embedded in design
4. `@pr-reviewer` — merge thread and CI

## Documentation expectations

Hot paths in merged code should carry:

- Comment or spec reference with O(·)
- Expected n source (NFR doc or inline assumption)
- Link to S3b advisory when exists

Missing documentation yields **pass-with-notes** minimum—not silent pass.
