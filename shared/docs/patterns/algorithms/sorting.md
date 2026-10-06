---
type: Algorithm Decision
title: Sorting decision table
description: "Choose a sort by stability, memory, and key assumptions at expected n."
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [latency, throughput, sort]
complexity_notes: O(n log n) typical; counting/radix when keys allow
skill_invoke: "@algorithm-advisor"
sources:
  - id: kb-clrs
    resource: ../knowledge-base/05-algorithms-clrs.md
    title: ADLC5 KB Part V — CLRS
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Decision table

| Situation | Prefer | Time | Notes |
|-----------|--------|------|-------|
| General comparison, stable | Merge sort | O(n log n) | Extra space |
| General, in-place | Heapsort | O(n log n) | Not stable |
| Average fast, in-place | Quicksort | O(n log n) avg | Worst O(n²); watch pivot |
| Small n or nearly sorted | Insertion sort | O(n²) worst | Often wins for tiny n |
| Integer keys in bounded range | Counting / radix | O(n+k) | Assumptions on keys |
| External / disk | B-tree based | — | Not in-memory sort |

## Agent rule

Prefer platform/stdlib sort unless constraints force a specific algorithm. Document expected `n`.

## Links

- Pattern wrapper: [/gof/strategy.md](/gof/strategy.md)
- Deep dive: [KB Part V §V.4](../knowledge-base/05-algorithms-clrs.md)
