---
type: Design Pattern
title: Decorator
description: Add responsibilities to an object at runtime without subclass explosion.
tags: [gof, hfdp, structural]
status: stable
scope: design
requirements_tags: [extensibility, composition]
related_patterns: [proxy, strategy]
gof_family: structural
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Need open-ended feature stacking without deep inheritance trees.

## Solution

Wrap component with decorator objects sharing the same interface; compose wrappers.

## When

Add features to an object at runtime; cross-cutting request handling layers.

## Often confused with

- **Strategy** — replaces algorithm; Decorator *adds*
- **Proxy** — controls access; Decorator extends behavior

## Caution

Wraps and adds responsibility; does not replace the core algorithm (Strategy).
