---
type: Algorithm Decision
title: String and text search
description: "Choose naive, Rabin-Karp, KMP, or platform index for text search at scale."
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [search, text]
complexity_notes: Prefer platform index at very large scale
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
| Single pattern, rare | Naive search |
| Multiple patterns / fingerprint | Rabin-Karp |
| Repeated same text | KMP / automata |
| Very large scale | Platform index (e.g. Elasticsearch) + CLRS for in-process core |

## Links

- [KB Part V §V.8](../knowledge-base/05-algorithms-clrs.md)
