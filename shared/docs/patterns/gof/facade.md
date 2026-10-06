---
type: Design Pattern
title: Facade
description: Provide a simple interface to a complex subsystem.
tags: [gof, hfdp, structural]
status: stable
scope: design
requirements_tags: [simplification, boundaries]
related_patterns: [adapter]
gof_family: structural
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Clients depend on too many subsystem types.

## Solution

Facade offers higher-level operations; subsystem stays internal.

## Often confused with

- **Adapter** — one-to-one interface translation

## Caution

Hide subsystem complexity behind a narrow API.
