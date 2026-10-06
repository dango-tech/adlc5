---
name: intake
description: Phase 1 — Intake for S7 Pattern Description authoring.
---

# Phase 1: Intake — Pattern Description

## Purpose

Verify catalog gates and load inputs before writing spec.

## Intake steps

### Step 1: Confirm S8 gate

Load S8 output:

- Decision must be **approve**
- Capture `roi_notes` summary for frontmatter

If not approved, **stop** — use GoF ad hoc via S3/S5.

### Step 2: Candidate identity

- Pattern ID (kebab-case)
- Working name
- S4 candidate file if exists

### Step 3: Load S10 exemplar analysis

If missing, recommend S10 before S7 or note gap in spec.

### Step 4: Implementation intent

Decide with user:

- skill | rule-only | hook

Drives S9 handoff.

### Step 5: Intake checklist

- [ ] S8 approved
- [ ] Pattern ID assigned
- [ ] S10 available or scheduled
- [ ] Implementation type chosen

Proceed to [02-analysis.md](02-analysis.md).
