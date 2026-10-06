---
type: Design Pattern
title: Abstract Factory
description: Create families of related products without specifying concrete classes.
tags: [gof, hfdp, creational]
status: stable
scope: design
requirements_tags: [creation, families, consistency]
related_patterns: [factory-method]
gof_family: creational
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Clients need consistent families of related objects.

## Solution

Abstract factory interface with methods per product; concrete factories for each family.

## Often confused with

- **Factory Method** — single product hierarchy

## Caution

Use when products must match as a set (theme, platform, vendor).
