---
name: intake
description: Phase 1 — Intake for S9 Piecemeal Implementation.
---

# Phase 1: Intake — Piecemeal Skill

## Purpose

Load S7 spec and choose artifact type for MVP.

## Intake steps

### Step 1: Load S7 spec

Path: `docs/patterns/<pattern-id>.md`

Extract:

- Variability points table
- `implementation` field value
- Related patterns

### Step 2: Confirm S8 approval

`roi_notes` present — gate satisfied.

### Step 3: Load S10 exemplar paths

For dry-run target.

### Step 4: Choose artifact type

| Type | When |
|------|------|
| skill | Multi-step guided workflow |
| rule-only | Always-on constraint |
| hook | Event-driven automation |

User approval required before creating files outside `skills/` scope.

### Step 5: Intake checklist

- [ ] S7 spec read
- [ ] Artifact type chosen
- [ ] Exemplar path for dry-run

Proceed to [02-analysis.md](02-analysis.md).
