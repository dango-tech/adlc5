---
type: Design Pattern
title: Proxy
description: "Control access to an object (lazy load, remote, protection)."
tags: [gof, hfdp, structural]
status: stable
scope: design
requirements_tags: [access-control, lazy-load, remote]
related_patterns: [decorator]
gof_family: structural
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Need a stand-in that controls access, defers cost, or mediates remoteness.

## Solution

Proxy implements subject interface and forwards to real subject with control logic.

## Caution

Controls access; Decorator adds behavior.
