---
name: output
description: Phase 3 — Output for S3. Deliver pattern recommendation and handoffs.
---

# Phase 3: Output — Design Pattern Advisor

## Purpose

Produce a design advisory consumable by Tasks code specs and S6 Implement review.

## Output steps

### Step 1: Write problem & forces section

Context-free problem statement plus quality attributes at stake (extensibility, testability, performance).

### Step 2: Recommendation table

| Pattern | Role in design | Why selected |

Maximum two primary patterns; note secondary supporting patterns if density justified.

### Step 3: Rejected alternatives

Bullet list with force-based rationale.

### Step 4: Variability points

Explicit list for S7/S10 if catalog path ever opens.

### Step 5: Optional interface sketch

Pseudocode or UML-lite—only if it clarifies roles (Context, Strategy, etc.).

### Step 6: Next steps / handoffs

- [ ] S3b for scale-sensitive algorithms
- [ ] S2 if ports/adapters unclear
- [ ] S5 if full requirements stack not yet mapped

Use [../templates/output-template.md](../templates/output-template.md).
