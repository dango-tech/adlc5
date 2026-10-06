---
type: Clean Code Principle
title: Functions do one thing
description: Small functions; one abstraction level; stepdown rule.
tags: [clean-code, readability, srp]
status: stable
scope: idiom
requirements_tags: [readability, srp]
skill_invoke: "@craftsmanship-code-review"
sources:
  - id: kb-cc
    resource: ../knowledge-base/02-clean-code.md
    title: ADLC5 KB Part II — Clean Code
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Guidance

Few arguments; no flag args; fail fast. Prefer parameter objects over long lists.

## Smell IDs

G30, F1 — see KB Part II §II.4.
