---
type: Design Pattern
title: Singleton
description: Ensure a class has exactly one instance with a global access point.
tags: [gof, hfdp, creational]
status: stable
scope: design
requirements_tags: [lifecycle]
related_patterns: []
gof_family: creational
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV — HFDP / GoF
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Problem

Exactly one shared instance is required.

## Solution

Controlled construction + shared accessor.

## Caution

Prefer composition-root single registration over classic Singleton when DI is available.

## Caution

Use sparingly — often global state abuse. Prefer DI of a single instance at composition root.
