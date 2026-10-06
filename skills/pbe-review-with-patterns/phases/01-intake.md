---
name: intake
description: Phase 1 — Intake for S6 Pattern Review.
---

# Phase 1: Intake — PBE Review with Patterns

## Purpose

Load claimed patterns and design artifacts before comparing to code.

## Intake steps

### Step 1: Claimed patterns

Extract from:

- PR description / template
- S5 pattern selection doc
- S3 design advisory
- `docs/patterns/<id>.md` if catalog pattern cited

### Step 2: Diff scope

Files changed vs design scope—flag if implementation wandered.

### Step 3: Catalog lookup

For each catalog ID, skim:

- Roles in Solution section
- Variability points table

### Step 4: Companion reviews

Note if S1/S3c already run—avoid duplicate findings; cross-link.

### Step 5: Intake checklist

- [ ] Claimed patterns listed
- [ ] S5/S3 artifact loaded or "undeclared" noted
- [ ] Diff scope identified

Proceed to [02-analysis.md](02-analysis.md).
