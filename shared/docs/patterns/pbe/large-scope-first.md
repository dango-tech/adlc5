---
type: PBE Pattern
title: Select large-scope patterns first
description: Architecture → design → algorithms → idioms; never invert.
tags: [pbe, architecture, selection]
status: stable
scope: architectural
requirements_tags: [architecture, selection]
skill_invoke: "@pbe-select-patterns"
sources:
  - id: kb-pbe
    resource: ../knowledge-base/01-pbe.md
    title: ADLC5 KB Part I — PBE
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Order

1. Architecture (ports/adapters, boundaries) — `@clean-architecture-review`
2. Design (GoF structure) — `@design-pattern-advisor`
3. Algorithm (O(·) at scale) — `@algorithm-advisor`
4. Idiom / catalog skill

## Links

- [/architecture/dependency-rule.md](/architecture/dependency-rule.md)
