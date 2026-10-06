---
type: Architecture Principle
title: Ports and Adapters
description: Depend on ports (interfaces); adapters implement details outward.
tags: [clean-architecture, hexagonal, dip]
status: stable
scope: architectural
requirements_tags: [hexagonal, dip]
skill_invoke: "@clean-architecture-review"
sources:
  - id: kb-ca
    resource: ../knowledge-base/03-clean-architecture.md
    title: ADLC5 KB Part III — Clean Architecture
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Essence

High-level policy depends on abstractions. Frameworks, DB, and UI plug in at the edges.

## Links

- [/architecture/dependency-rule.md](/architecture/dependency-rule.md)
- Skill: `@clean-architecture-review`
