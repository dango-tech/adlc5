---
name: analysis
description: Phase 2 — Analysis for S1. Apply G/F/N/T smell heuristics, test quality, error handling, and AI slop checks.
---

# Phase 2: Analysis — Craftsmanship Code Review

## Purpose

Systematically evaluate changed hunks against Clean Code heuristics. Every actionable finding must cite a smell ID.

## Analysis order

Work top-down: names → functions → general smells → tests → errors → AI slop.

### 1. Names (N)

For each new or renamed symbol in the diff:

- Is the name intention-revealing at call site?
- One word per concept across the module?
- Searchable (no single-letter except loop indices)?
- Flag N1, N2, N3 with file:line.

### 2. Functions (F, G30)

For each new or modified function:

- Lines of code and abstraction levels — one thing only (G30)?
- Argument count — F1 if >3 without object?
- Dead code introduced or left behind — F4?
- Stepdown rule: reads top-to-bottom?

### 3. General smells (G)

Scan changed hunks for:

| Priority | IDs | Look for |
|----------|-----|----------|
| High | G5 | Duplicated blocks, parallel conditionals |
| High | G6 | Framework/IO mixed with business logic |
| Medium | G14 | Feature envy across types |
| Medium | G23 | Type-switch where polymorphism fits |

### 4. Tests (T1–T9)

For each production change:

- New behavior has tests? (T1)
- Tests assert behavior not internals? (T5)
- Boundaries: empty, null, max, error paths?
- Test code as clean as production?
- Learning tests at third-party boundaries?

### 5. Error handling

- Exceptions vs error codes — project convention followed?
- Fail fast on invalid preconditions?
- Third-party APIs wrapped at boundary?
- No swallowed exceptions without logging?

### 6. AI slop scan

Per `ai-slop-cleanup.mdc` in changed hunks only:

- Obvious narrating comments
- Redundant null guards after validation
- `as any` / unsafe casts
- Debug `console.log` / `print` left in
- Over-abstracted one-use helpers

### 7. Boy Scout opportunities

Note safe micro-improvements **in touched hunks only** — do not expand scope.

## Severity assignment

| Severity | Definition |
|----------|------------|
| **blocking** | Merge should wait — missing critical tests, egregious duplication in hot path |
| **major** | Fix before or immediately after merge |
| **minor** | Style/clarity; ticket optional |
| **info** | Strength or observation |

## Escalation triggers

During analysis, route out if:

- Import direction / layer leak → stop S1 scope; recommend S2
- Pattern roles missing → note for S6
- Nested loops without documented n → note for S3c

## Analysis checklist

- [ ] All changed files reviewed
- [ ] Every finding has smell ID
- [ ] Tests evaluated for changed behavior
- [ ] AI slop checked in diff hunks only
- [ ] Escalations noted

Proceed to [03-output.md](03-output.md).
