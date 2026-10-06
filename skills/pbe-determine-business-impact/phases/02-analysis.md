---
name: analysis
description: Phase 2 — Analysis for S8. ROI calculation, risks, decision.
---

# Phase 2: Analysis — Determine Business Impact

## Purpose

Produce defendable approve/defer/reject decision.

## Analysis steps

### 1. Restate candidate

Problem + solution shape in context-free language.

### 2. Rule of Three verification

Re-verify S4 evidence independently—reject padded contexts.

### 3. Recurrence forecast

Expected occurrences next 12 months:

- New features touching this force
- Teams adopting pattern

Label assumptions.

### 4. Hours saved per occurrence

Without catalog:

- Design time, review churn, defect fix, onboarding

With catalog:

- Reduced but non-zero (spec reading, skill invoke)

### 5. Production cost

Sum S7 + S10 + S9 + maintenance (annualized).

### 6. Net ROI

Apply formula; note qualitative factors if numbers weak.

### 7. Risk assessment

| Risk | Mitigation |
|------|------------|
| Perfect Pattern | S9 MVP only |
| Stale spec | Version + owner |
| Wrong abstraction | S10 validation |

### 8. Decision

approve | defer | reject with one-paragraph rationale.

Proceed to [03-output.md](03-output.md).
