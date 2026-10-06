---
type: Design Pattern
title: State
description: "Alter behavior when an object's internal state changes."
tags: [gof, hfdp, behavioral]
status: stable
scope: design
requirements_tags: [modes, workflows]
related_patterns: [strategy]
gof_family: behavioral
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Large switches on mode/type drive divergent behavior.

## Solution

State objects implement shared interface; context delegates; transitions change current state.

## Often confused with

- **Strategy** — external algorithm vs internal mode

## Caution

State swaps by internal mode; Strategy swaps by external algorithm choice.
