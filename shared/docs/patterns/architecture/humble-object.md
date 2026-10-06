---
type: Architecture Principle
title: Humble Object
description: Push hard-to-test edges behind boundaries; keep core unit-testable.
tags: [clean-architecture, testability, boundaries]
status: stable
scope: architectural
requirements_tags: [testability, boundaries]
skill_invoke: "@clean-architecture-review"
sources:
  - id: kb-ca
    resource: ../knowledge-base/03-clean-architecture.md
    title: ADLC5 KB Part III — Clean Architecture
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Essence

UI, DB, and device I/O stay humble; policy lives in testable use cases.
