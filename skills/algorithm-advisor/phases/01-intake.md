---
name: intake
description: Phase 1 — Intake for S3b Algorithm Advisor. Capture scale NFRs and problem classification inputs.
---

# Phase 1: Intake — Algorithm Advisor

## Purpose

Quantify scale and classify the algorithmic problem before consulting decision tables.

## Intake steps

### Step 1: Scale NFRs

Extract or ask:

| NFR | Value |
|-----|-------|
| Expected n (typical / peak) | |
| Latency target (p50 / p99) | |
| Throughput (req/s, events/s) | |
| Memory budget | |
| Growth horizon (12 mo) | |

If all unknown and scope is CRUD/admin, consider N/A path.

### Step 2: Problem statement

Describe operation in domain terms:

- "Find nearest warehouse for each order line"
- "Merge sorted audit streams"
- Not "need a hash map" (implementation premature)

### Step 3: Classify problem domain

Tag one primary class:

- sorting | search/lookup | graph | optimization | string/text | other

Point to playbook section (V.4–V.8).

### Step 4: Constraints

- Mutable vs immutable data
- Online vs offline / batch
- External memory (disk) allowed?
- Parallelism available?

### Step 5: Link to design context

- S3 Strategy variant needing algorithm?
- S2 layer where logic lives?

### Step 6: Intake checklist

- [ ] n estimated with source (req doc, metrics, assumption labeled)
- [ ] Problem domain classified
- [ ] N/A criteria evaluated

Proceed to [02-analysis.md](02-analysis.md).
