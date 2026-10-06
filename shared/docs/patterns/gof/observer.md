---
type: Design Pattern
title: Observer
description: One-to-many notification when subject state changes.
tags: [gof, hfdp, behavioral]
status: stable
scope: design
requirements_tags: [events, ui, decoupling]
related_patterns: [command]
gof_family: behavioral
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Dependents must react when a subject's state changes without tight coupling.

## Solution

Subject maintains observer list; notifies on change; observers implement a common update interface.

## When

UI/widgets reacting to model; domain events within a bounded context.

## Often confused with

- Polling — Observer is push notification
- Event bus at system scale — different operational concerns

## Caution

Often confused with polling or a global event bus (different scale).
