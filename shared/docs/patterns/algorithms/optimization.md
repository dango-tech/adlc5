---
type: Algorithm Decision
title: Optimization paradigms
description: "Pick DP, greedy, or exact/heuristic methods from problem structure."
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [optimization, scheduling]
complexity_notes: DP when overlapping subproblems; greedy only with proof
skill_invoke: "@algorithm-advisor"
sources:
  - id: kb-clrs
    resource: ../knowledge-base/05-algorithms-clrs.md
    title: ADLC5 KB Part V — CLRS
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Decision table

| Situation | Approach |
|-----------|----------|
| Overlapping subproblems + optimal substructure | Dynamic programming |
| Greedy-choice proven | Greedy |
| Brute force exponential | Check NP-completeness; approximate/heuristic |
| Need optimal, small input | DP or specialized exact algo |

## Paradigms

See also [/algorithms/dynamic-programming.md](/algorithms/dynamic-programming.md) and [/algorithms/greedy.md](/algorithms/greedy.md).

## Links

- [KB Part V §V.3, §V.7](../knowledge-base/05-algorithms-clrs.md)
