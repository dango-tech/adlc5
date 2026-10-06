---
type: Algorithm Decision
title: Search and lookup decision table
description: "Choose hash, BST, binary search, heap, or union-find from access patterns."
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [latency, search, lookup]
complexity_notes: Hash O(1) avg; BST/binary search O(log n)
skill_invoke: "@algorithm-advisor"
sources:
  - id: kb-clrs
    resource: ../knowledge-base/05-algorithms-clrs.md
    title: ADLC5 KB Part V — CLRS
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Decision table

| Situation | Prefer | Average | Notes |
|-----------|--------|---------|-------|
| Static set, no order | Hash table | O(1) | Collision strategy |
| Ordered set, range queries | Balanced BST | O(log n) | In-order traversal |
| Static sorted array | Binary search | O(log n) | No mutation |
| Priority / scheduling | Binary heap | O(log n) insert/extract | Not full sort |
| Frequent union-find | Disjoint-set forest | Nearly O(α(n)) | Connectivity, MST |

## Anti-patterns

- Hash table when ordering or range queries are required
- Exotic structures when hash map or array suffices

## Links

- [KB Part V §V.5](../knowledge-base/05-algorithms-clrs.md)
