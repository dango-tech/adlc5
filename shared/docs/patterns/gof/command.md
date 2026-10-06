---
type: Design Pattern
title: Command
description: "Encapsulate a request as an object for queues, undo, or macros."
tags: [gof, hfdp, behavioral]
status: stable
scope: design
requirements_tags: [undo, queues, macros]
related_patterns: [observer]
gof_family: behavioral
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Need to parameterize, queue, log, or undo operations.

## Solution

Command object binds receiver + action; invoker triggers without knowing details.

## Caution

Turns an invocation into a first-class object.
