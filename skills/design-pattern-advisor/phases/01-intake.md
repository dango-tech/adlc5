---
name: intake
description: Phase 1 — Intake for S3 Design Pattern Advisor. Capture problem, forces, and constraints.
---

# Phase 1: Intake — Design Pattern Advisor

## Purpose

Frame the design problem in terms of forces and variation—not pattern names.

## Intake steps

### Step 1: Problem statement

Ask or extract:

- What behavior must change over time?
- What is painful today (switch statements, subclass explosion, tight coupling)?
- Who are the clients and what do they need from the abstraction?

Write one paragraph **without** naming a GoF pattern.

### Step 2: Variation inventory

List dimensions of change:

- Algorithms, states, notification targets, product families, tree structures, etc.

Mark stable vs volatile elements.

### Step 3: Constraints

| Constraint | Value |
|------------|-------|
| Scale NFRs | yes/no — if yes, flag S3b |
| Architectural layer | from S2 if available |
| Platform / language | affects idioms |
| Testability needs | mock-friendly interfaces? |

### Step 4: Existing code context

- Greenfield vs refactor
- Relevant files or class diagrams
- Anti-target: what solutions were already rejected?

### Step 5: Intake checklist

- [ ] Problem stated without pattern name
- [ ] Variation points listed
- [ ] Constraints captured
- [ ] S2 boundary review done or scheduled

Proceed to [02-analysis.md](02-analysis.md).
