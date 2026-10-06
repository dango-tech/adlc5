---
type: Algorithm Decision
title: Dynamic programming
description: Optimal substructure with overlapping subproblems — memoize or tabulate.
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [optimization, overlapping-subproblems]
complexity_notes: Usually poly time after memoization; space depends on table
skill_invoke: "@algorithm-advisor"
sources:
  - id: kb-clrs
    resource: ../knowledge-base/05-algorithms-clrs.md
    title: ADLC5 KB Part V — CLRS
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Use when

Optimal substructure **and** overlapping subproblems.

## Approach

Memoize recursive solution or bottom-up tabulation. State the DP state and transition.

## Caution

Without overlapping subproblems, prefer divide-and-conquer.

## Links

- [/algorithms/optimization.md](/algorithms/optimization.md)
