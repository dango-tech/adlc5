---
type: Design Pattern
title: Iterator
description: Sequential access to aggregate elements without exposing structure.
tags: [gof, hfdp, behavioral]
status: stable
scope: design
requirements_tags: [collections, encapsulation]
related_patterns: [composite]
gof_family: behavioral
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Traverse a collection without leaking internal representation.

## Solution

Iterator interface (next/hasNext or equivalent); aggregate creates iterators.

## Caution

Prefer language/stdlib iterators when available.
