---
type: PBE Pattern
title: Pattern selection driven by requirements
description: Map functional reqs and NFRs to patterns via tags — not pattern shopping.
tags: [pbe, requirements, nfr]
status: stable
scope: design
requirements_tags: [requirements, nfr]
skill_invoke: "@pbe-select-patterns"
sources:
  - id: kb-pbe
    resource: ../knowledge-base/01-pbe.md
    title: ADLC5 KB Part I — PBE
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Essence

Start from requirements and NFR tags; search catalog `requirements_tags`; fill gaps with GoF.

## Skill

`@pbe-select-patterns` — read [/index.md](/index.md) then matching concept files.
