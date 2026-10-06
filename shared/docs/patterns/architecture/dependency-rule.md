---
type: Architecture Principle
title: Dependency Rule
description: Source dependencies point inward; inner circles know nothing about outer.
tags: [clean-architecture, boundaries, layers]
status: stable
scope: architectural
requirements_tags: [boundaries, layers]
skill_invoke: "@clean-architecture-review"
sources:
  - id: kb-ca
    resource: ../knowledge-base/03-clean-architecture.md
    title: ADLC5 KB Part III — Clean Architecture
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Layers (inside → outside)

1. Entities
2. Use cases
3. Interface adapters
4. Frameworks & drivers (details)

## Agent checks

- Import direction violates dependency rule?
- Business logic in controllers or framework hooks?
