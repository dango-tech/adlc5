---
name: intake
description: Phase 1 — Intake for S5 Pattern Selection.
---

# Phase 1: Intake — PBE Select Patterns

## Purpose

Load requirements and catalog context before mapping patterns.

## Intake steps

### Step 1: Load requirements

| Source | Extract |
|--------|---------|
| PRT / PRD | Functional requirements |
| NFR section | latency, throughput, volume |
| UX spec | Interaction patterns affecting adapters |

Number or ID each requirement for traceability.

### Step 2: Tag NFRs

Tags for catalog search: `search`, `latency`, `batch`, `auth`, `multi-tenant`, etc.

### Step 3: Catalog inventory (OKF)

1. `./scripts/adlc5 patterns lookup --tags …` (ids/paths only) — or read `shared/docs/patterns/index.md`
2. Open **at most one** relevant group `index.md`
3. Open **≤3** matching concept cards (`requirements_tags`, `related_patterns`) — never the full catalog:

- Candidate hits by tag
- Related pattern chains (concept ids)

### Step 4: Prior Engineer artifacts

- S2 layer map (if exists)
- S3 advisory (if narrow problem pre-solved)

### Step 5: Intake checklist

- [ ] Requirements enumerated
- [ ] NFR tags assigned
- [ ] Catalog searched
- [ ] S2 status known

Proceed to [02-analysis.md](02-analysis.md).
