---
type: Design Pattern
title: Factory Method
description: Subclass (or override) decides which concrete product to create.
tags: [gof, hfdp, creational]
status: stable
scope: design
requirements_tags: [creation, decoupling]
related_patterns: [abstract-factory, strategy]
gof_family: creational
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

`new` scattered; creation type must vary by context without callers knowing concrete classes.

## Solution

Creator exposes factory method; subclasses return concrete products.

## Often confused with

- **Abstract Factory** — families of products vs one product line

## Caution

One product lineage; Abstract Factory covers families of related products.
