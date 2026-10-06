---
name: analysis
description: Phase 2 — Analysis for S3. Apply seven principles and GoF decision tables.
---

# Phase 2: Analysis — Design Pattern Advisor

## Purpose

Match problem forces to 1–2 GoF patterns with explicit rejection rationale.

## Analysis steps

### 1. Apply seven principles

For each principle, one sentence on how it applies to this problem. Flag violations in current design if brownfield.

### 2. Consult OKF catalog (then KB if needed)

1. Prefer `./scripts/adlc5 patterns lookup --tags … --group gof` (ids/paths)
2. Read `shared/docs/patterns/gof/index.md` only if needed
3. Open **1–3** matching `gof/<slug>.md` cards by forces / tags — never the full catalog
4. Check each card's "Often confused with"
5. Only if cards lack detail: open KB Part IV §IV.3–IV.4

### 3. Generate candidates

List 2–3 candidate patterns. Score each:

| Criterion | Weight |
|-----------|--------|
| Encapsulates identified variation | high |
| OCP for expected extensions | high |
| Team familiarity / simplicity | medium |
| Testability | medium |

### 4. Select primary + reject others

Document:

- **Recommended** — pattern name, role, why it wins
- **Rejected** — each alternative and specific reason (not "too complex" alone)

### 5. Variability points

Table or bullets:

- What is fixed (context, interface)
- What varies (strategies, states, decorators, products)

### 6. Density check

Do complementary patterns integrate?

- Example: Strategy inside Factory for algorithm families
- Flag if >3 patterns with no collaboration story

### 7. Catalog discipline

- Cite OKF concept ids (`gof/strategy`) for chosen patterns
- Community seed cards are fine for advisory; org-specific ROI assets still require S4 → S8
- New org entry: defer to S4 → S8 → S7 (write OKF concept + update indexes)

### 8. Scale flag

If Strategy or search/sort/graph inside pattern:

- Note expected n, latency
- Schedule S3b for algorithm choice

Proceed to [03-output.md](03-output.md).
