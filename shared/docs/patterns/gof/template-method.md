---
type: Design Pattern
title: Template Method
description: Define algorithm skeleton in a base class; subclasses vary steps.
tags: [gof, hfdp, behavioral]
status: stable
scope: design
requirements_tags: [variation, inheritance]
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

Algorithm structure is fixed; some steps vary.

## Solution

Base class implements skeleton calling overridable hooks.

## Often confused with

- **Strategy** — composition vs inheritance for variation

## Caution

Inheritance-based variation; prefer Strategy (composition) when steps are independently swappable.
