---
type: Architecture Principle
title: Screaming Architecture
description: "Project structure should scream use cases, not framework names."
tags: [clean-architecture, structure, use-cases]
status: stable
scope: architectural
requirements_tags: [structure, use-cases]
skill_invoke: "@clean-architecture-review"
sources:
  - id: kb-ca
    resource: ../knowledge-base/03-clean-architecture.md
    title: ADLC5 KB Part III — Clean Architecture
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Essence

Organize by use case / bounded context, not by "controllers/", "models/" as the primary story.
