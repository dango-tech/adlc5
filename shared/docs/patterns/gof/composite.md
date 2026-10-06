---
type: Design Pattern
title: Composite
description: Treat individual objects and compositions uniformly in a tree.
tags: [gof, hfdp, structural]
status: stable
scope: design
requirements_tags: [trees, ui, ast]
related_patterns: [iterator, decorator]
gof_family: structural
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Clients must treat leaves and groups the same way.

## Solution

Component interface; leaf and composite implement it; composite holds children.

## Caution

Part-whole hierarchies: UI trees, org charts, ASTs.
