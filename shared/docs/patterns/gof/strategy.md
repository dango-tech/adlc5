---
type: Design Pattern
title: Strategy
description: Interchangeable algorithms or behaviors behind a common interface.
tags: [gof, hfdp, behavioral]
status: stable
scope: design
requirements_tags: [extensibility, algorithms, variation]
related_patterns: [state, factory-method]
gof_family: behavioral
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Multiple algorithms for the same job; clients must not hard-code the choice.

## Solution

Define a strategy interface; inject concrete strategies; client depends on the abstraction.

## When

Many algorithms for same job; need to swap behavior without editing callers.

## Variability

- Fixed: context API and strategy interface
- Varies: concrete algorithm implementations

## Often confused with

- **State** — swaps behavior by *internal mode*, not external algorithm choice
- Large if/else — Strategy replaces branching with polymorphism

## Related catalog

- Algorithms: [/algorithms/sorting.md](/algorithms/sorting.md), [/algorithms/search-lookup.md](/algorithms/search-lookup.md)
- Deep dive: [KB Part IV](../knowledge-base/04-design-patterns.md)

## Caution

Often confused with large if/else or State. Pair with CLRS for which algorithm each strategy runs.
