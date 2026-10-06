---
name: analysis
description: Phase 2 — Analysis for S5. Map requirements to pattern stack with density.
---

# Phase 2: Analysis — PBE Select Patterns

## Purpose

Build integrated pattern stack large-scope first.

## Analysis steps

### 1. Requirements ↔ patterns matrix

For each requirement:

- Architectural need?
- Design pattern?
- Algorithm?
- Catalog ID or GoF name?

### 2. Architecture layer (S2)

If boundaries not clear, **stop** and recommend S2 before finalizing S5.

Document ports/adapters, use cases, screaming folders.

### 3. Design layer (S3 logic)

For each variation point:

- GoF pattern name
- Rejected alternatives (brief)

### 4. Algorithm layer (S3b)

If any requirement tagged with scale:

- Invoke or reference S3b
- Document O(·) in layer stack

### 5. Catalog vs GoF

| Pattern need | Source |
|--------------|--------|
| In catalog | `docs/patterns/<id>` |
| Not in catalog | GoF ad hoc; note S4/S8 if recurrence likely |

### 6. Density check

Patterns must collaborate:

- Example: Repository (port) + Factory (creation) + Strategy (pricing)
- Flag isolated patterns with no integration story

### 7. Variability points

What adapts per tenant/feature vs fixed scaffold.

Proceed to [03-output.md](03-output.md).
