# Pattern catalog (OKF bundle)

Org-level **Patterns-Based Engineering (PBE)** catalog for ADLC5, stored as an **[OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)** knowledge bundle.

**Agent entrypoint:** [index.md](index.md) (progressive disclosure). Concept ID = path without `.md`.

**Efficient use:** Prefer `./scripts/adlc5 patterns lookup --tags …` (ids/paths only); never paste the full catalog into a turn.

**Rule of Three:** Same problem/solution in three unique situations → candidate pattern. Document evidence before cataloging.

**ROI gate (S8):** Promote org-specific assets here when recurrence and business impact justify maintenance. Community GoF/CLRS seeds below are stable references for skills — not a claim that every GoF pattern passed S8 as an org asset.

## Bundle layout

```text
shared/docs/patterns/          # OKF bundle root
├── index.md                   # OKF root index (okf_version: "0.2")
├── log.md                     # OKF update history
├── README.md                  # This file — human governance
├── gof/                       # Design Pattern concepts
├── algorithms/                # Algorithm Decision concepts
├── pbe/                       # PBE Pattern concepts
├── architecture/              # Architecture Principle concepts
└── clean-code/                # Clean Code Principle concepts
```

Each concept is one markdown file with YAML frontmatter. Required OKF field: `type`. ADLC5 extensions (`scope`, `requirements_tags`, `related_patterns`, `skill_invoke`, `complexity_notes`) are producer-defined keys (OKF allows them).

## Frontmatter (OKF + ADLC5)

```yaml
---
type: Design Pattern            # OKF required — also: Algorithm Decision, PBE Pattern, …
title: Strategy
description: One-line summary for index snippets
tags: [gof, hfdp, behavioral]
status: stable                  # draft | stable | deprecated
scope: design                   # architectural | design | idiom | algorithmic
requirements_tags: [latency, extensibility]
related_patterns: [state]
skill_invoke: "@design-pattern-advisor"
sources:
  - id: kb-hfdp
    resource: ../knowledge-base/04-design-patterns.md
    title: ADLC5 KB Part IV
generated: { by: process:adlc5-okf-seed, at: 2026-08-09T06:50:00Z }
---
```

## Tool load protocol (hard rules)

1. **Default:** read only `shared/docs/patterns/index.md` (or one group `index.md`) — never paste the full catalog or many cards into chat.
2. **Lookup first:** `./scripts/adlc5 patterns lookup --tags …` (or `./scripts/patterns/lookup.sh`) — prints matching **ids/paths** (optional short frontmatter); do not glob-read every concept.
3. **Cards:** open **at most 1–3** matching concept `.md` files for the current problem tags.
4. **KB essays** under `shared/docs/knowledge-base/` — only if the card is insufficient.
5. **Cite ids** (`gof/strategy`) in design docs / S5 output — do not embed card bodies.
6. **Build / implementer packs:** do **not** attach catalog cards unless the story explicitly names a pattern to apply.

Skills: `@design-pattern-advisor`, `@algorithm-advisor`, `@pbe-select-patterns`, `@clean-architecture-review`.

## Workflow (org assets)

1. **S4** — Identify pattern opportunity during delivery.
2. **S8** — Determine business impact / ROI.
3. **S7** — Write OKF concept under the appropriate subdirectory (or new group with its own `index.md`).
4. **S9** — Piecemeal skill or rule for consumability.
5. **S6** — Review deliverables with pattern names and variability points.
6. Update root + group `index.md` and `log.md`.

See [../knowledge-base/01-pbe.md](../knowledge-base/01-pbe.md) and [../playbook.md](../playbook.md).
