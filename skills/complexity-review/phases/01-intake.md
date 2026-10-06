---
name: intake
description: Phase 1 — Intake for S3c Complexity Review. Load diff, S3b advisory, and NFRs.
---

# Phase 1: Intake — Complexity Review

## Purpose

Connect PR diff to documented scale expectations before analyzing hot paths.

## Intake steps

### Step 1: Scope diff

- PR link or file list
- Highlight files with loops, recursion, batch I/O, aggregations

### Step 2: Load S3b artifact

Search for:

- Engineer algorithm advisory in design docs
- O(·) notes in code spec or PR description
- Delivery `.adlc5/` / `.fsd3/` implementation spec

If missing but diff is hot-path heavy, note **documentation gap**.

### Step 3: Load NFRs

| Field | Source |
|-------|--------|
| Expected n | PRD / S3b / assumption |
| Latency | NFR doc |
| S3b status | advisory / N/A |

### Step 4: N/A check

S3c N/A when **all** true:

- No loops over unbounded collections in diff
- No new search/sort/graph/batch paths
- S3b marked N/A with justified small n

If any false, proceed with full review.

### Step 5: Intake checklist

- [ ] Diff scoped
- [ ] S3b / O(·) doc located or gap noted
- [ ] N/A criteria evaluated

Proceed to [02-analysis.md](02-analysis.md).
