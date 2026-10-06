---
type: Design Pattern
title: Adapter
description: Translate an incompatible interface into one clients expect.
tags: [gof, hfdp, structural]
status: stable
scope: design
requirements_tags: [integration, legacy]
related_patterns: [facade]
gof_family: structural
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Legacy or third-party API does not match client expectations.

## Solution

Adapter implements target interface and delegates to adaptee.

## Often confused with

- **Facade** — simplifies many classes; Adapter bridges one mismatch

## Caution

Adapts one interface; Facade simplifies a whole subsystem.
