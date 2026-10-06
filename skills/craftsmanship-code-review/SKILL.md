---
name: craftsmanship-code-review
description: >-
  Clean Code review using G/F/N/T smell heuristics. Use during Implement for PR
  review, diff review, or post-implementation quality gate. Invoke with
  @craftsmanship-code-review.
---

# S1 — Craftsmanship Code Review

**ADLC5 stage:** Implement (verification / PR review)
**Skill ID:** S1  
**Knowledge base:** [Part II — Clean Code](../../shared/docs/knowledge-base/02-clean-code.md)  
**Rules:** R3 `cc-functions-and-tests.mdc`, `ai-slop-cleanup.mdc`  
**Playbook:** Part II §II.4 (smell heuristics), Appendix G (full G/F/N/T catalog)

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Apply Clean Code craftsmanship at the line and function level. S1 complements architecture (S2), pattern (S3/S6), and complexity (S3c) reviews by focusing on readability, maintainability, test quality, and AI-generated noise in changed code.

## When to invoke

- PR or diff review before merge (`@pr-reviewer` companion)
- `implement-2-verify` code-quality verification
- Post-refactor sanity check on touched files
- User asks for Clean Code review or smell analysis
- Implement quality gate before merge

**Do not invoke for:** architecture boundaries (use S2), pattern selection (S3/S5), or hot-path complexity (S3c).

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Scope, diff, language, prior reviews |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | G/F/N/T heuristics, tests, AI slop |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Verdict, findings table, checklist |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Scope** — Identify files/changes under review; note language and test coverage.
2. **Names (N)** — Check intention-revealing names; one word per concept; searchable identifiers (N1).
3. **Functions (F, G30, F1, F4)** — Small, one thing, one abstraction level; few args; no dead code.
4. **General (G)** — Duplication (G5), wrong abstraction level (G6), feature envy (G14), prefer polymorphism over switch (G23).
5. **Tests (T1–T9)** — FIRST properties; boundary cases; test code quality; learning tests at boundaries.
6. **Error handling** — Exceptions over error codes; no gratuitous null returns; third-party APIs wrapped.
7. **AI slop** — Obvious comments, defensive guards, `as any`, debug logs (see `ai-slop-cleanup.mdc`).
8. **Boy Scout** — Note small improvements safe to make in touched hunks.

## Smell heuristic quick reference

### Names (N)

| ID | Smell | Signal |
|----|-------|--------|
| N1 | Non-descriptive name | `d`, `temp`, `data`, `handler2` |
| N2 | Inconsistent vocabulary | `getUser` vs `fetchAccount` for same concept |
| N3 | Misleading name | Method name promises side effect it lacks |

### Functions (F)

| ID | Smell | Signal |
|----|-------|--------|
| F1 | Too many arguments | >3 args without parameter object |
| F4 | Dead function | Unreachable or never called |
| G30 | Does more than one thing | Multiple abstraction levels in one function |

### General (G)

| ID | Smell | Signal |
|----|-------|--------|
| G5 | Duplication | Copy-paste blocks; parallel switch/if chains |
| G6 | Wrong abstraction level | Low-level details mixed with policy |
| G14 | Feature envy | Method uses another object's data more than its own |
| G23 | Switch over type | Prefer polymorphism or Strategy |

### Tests (T)

| ID | Smell | Signal |
|----|-------|--------|
| T1 | Insufficient tests | No boundary or error-path coverage |
| T5 | Fragile tests | Assert implementation details, not behavior |
| T7 | Slow tests | Unit tests requiring network/DB unnecessarily |

## Integration with ADLC5

```
Plan (S2, S3, S3b) → Implement build → Verify/PR (S1 + S3c + S6 + @pr-reviewer)
```

- Run S1 on every PR with non-trivial code changes.
- If S1 finds G6 (wrong abstraction), escalate to S2.
- If S1 finds nested loops on large n, escalate to S3c.
- Pair with S6 when pattern vocabulary should appear in review comments.

## Output format

```markdown
## Craftsmanship Code Review — [scope]

**Verdict:** pass | pass-with-notes | fail

### Findings (by severity)

| ID | Smell | Location | Recommendation |
|----|-------|----------|----------------|
| G5 | Duplication | `path:line` | Extract shared … |

### Strengths
- …

### Suggested fixes (priority order)
1. …

### Checklist
- [ ] Names (N)
- [ ] Functions (F/G30)
- [ ] Tests (T)
- [ ] Error handling
- [ ] No AI slop in changed hunks
```

Cite smell IDs (G/F/N/T) for every actionable finding. Full heuristic list: playbook Part II §II.4 and Appendix G.

## Verdict criteria

| Verdict | Criteria |
|---------|----------|
| **pass** | No blocking smells; minor notes optional |
| **pass-with-notes** | Non-blocking issues; safe to merge with follow-up tickets |
| **fail** | Blocking smells (untested critical path, egregious duplication, security-adjacent error handling) |

## Handoffs

| Finding type | Route to |
|--------------|----------|
| Layer / dependency leak | S2 `@clean-architecture-review` |
| Pattern mismatch | S6 `@pbe-review-with-patterns` |
| Hot-path O(n²)+ | S3c `@complexity-review` |
| Merge blockers + comments | `@pr-reviewer` |

## Anti-patterns for reviewers

- Nitpicking style outside project conventions
- Reviewing files outside the diff scope without reason
- Suggesting rewrites without citing smell IDs
- Ignoring test quality in favor of production code only
