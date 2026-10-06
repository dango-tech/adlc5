---
name: analysis
description: Phase 2 — Analysis for S3c. Analyze hot paths, state O(·), scan anti-patterns and N+1.
---

# Phase 2: Analysis — Complexity Review

## Purpose

Derive actual complexity from code and compare to stated expectations.

## Analysis steps

### 1. Enumerate hot paths

For each path in diff:

| Path name | Entry function | Line range |
|-----------|----------------|------------|

Include: nested loops, recursive calls, stream aggregations, DB/API in loops.

### 2. Derive O(·)

For each hot path:

- Count nested iterations over n
- Account for hidden factors (DB round-trips = multiply by query count)
- State time and space

Compare **stated** (from S3b/spec) vs **observed**.

### 3. Expected n check

At documented n, is observed complexity acceptable?

- Example: O(n log n) at n=10⁶ → OK; O(n²) → fail

### 4. Anti-pattern scan

Apply V.9 checklist (AP1–AP6). Record hits with location.

### 5. N+1 / I/O patterns

- ORM lazy load in loop
- HTTP call per item
- Unbounded parallel fan-out

### 6. Cold vs hot

Flag AP4 if micro-optimizations appear on cold paths while hot path remains poor.

### 7. Documentation gap

List missing O(·) comments or spec entries.

Proceed to [03-output.md](03-output.md).
