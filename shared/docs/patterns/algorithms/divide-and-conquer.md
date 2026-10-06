---
type: Algorithm Decision
title: Divide and conquer
description: Split into independent subproblems; combine results (Master theorem).
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [recursion, parallelism]
complexity_notes: Combine step can dominate — analyze carefully
skill_invoke: "@algorithm-advisor"
sources:
  - id: kb-clrs
    resource: ../knowledge-base/05-algorithms-clrs.md
    title: ADLC5 KB Part V — CLRS
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Use when

Subproblems are independent (unlike DP overlaps).

## Analysis

Define recurrence; apply Master theorem or tree method. State O(·) for combine.

## Links

- [KB Part V §V.2–V.3](../knowledge-base/05-algorithms-clrs.md)
