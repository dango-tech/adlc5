---
type: Algorithm Decision
title: CLRS agent anti-patterns
description: Hot-path mistakes to reject during algorithm advisory and complexity review.
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [latency, correctness]
complexity_notes: N/A — checklist
skill_invoke: "@algorithm-advisor"
sources:
  - id: kb-clrs
    resource: ../knowledge-base/05-algorithms-clrs.md
    title: ADLC5 KB Part V — CLRS
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Reject these

- O(n²) nested loops on large `n` without justification
- Dijkstra with negative edge weights
- Greedy without greedy-choice proof
- Hash table when ordering or range queries required
- Exotic structures when hash map or array suffices
- Micro-optimizing cold paths while hot path stays quadratic
- Brute-force exponential on large inputs

## Links

- Skill: `@algorithm-advisor`, `@complexity-review`
- [KB Part V §V.9](../knowledge-base/05-algorithms-clrs.md)
