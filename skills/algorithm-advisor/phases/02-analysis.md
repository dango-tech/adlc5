---
name: analysis
description: Phase 2 — Analysis for S3b. Apply CLRS decision tables and complexity analysis.
---

# Phase 2: Analysis — Algorithm Advisor

## Purpose

Select algorithm/DS with documented O(·) and rejected alternatives.

## Analysis steps

### 1. Consult OKF decision card

Prefer `./scripts/adlc5 patterns lookup --tags … --group algorithms`. Open **one** `shared/docs/patterns/algorithms/<class>.md` for the problem class (≤3 total if paradigms also needed):

- Sorting → `algorithms/sorting`
- Search/lookup → `algorithms/search-lookup`
- Graph → `algorithms/graph`
- Optimization → `algorithms/optimization`
- String/text → `algorithms/string-text`

List 2–3 table candidates applicable to constraints. Note prerequisites (e.g., sorted input, DAG not general graph). Open KB Part V only if the card is insufficient. Never dump the algorithms group.

### 2. Prefer platform/stdlib

Before custom implementation:

- Language stdlib (sort, heap, map)
- Database index / query planner
- Managed service (search engine)

Document when stdlib is sufficient at expected n.

### 3. Compute O(·)

For chosen approach:

| | Time | Space |
|---|------|-------|
| Worst case | | |
| Average case | | |
| At expected n | dominant term | |

### 4. Reject alternatives

| Option | Why rejected |
|--------|--------------|
| Brute force | n too large |
| O(n log n) sort + scan | … |

### 5. Paradigm check

- **DP:** overlapping subproblems + optimal substructure?
- **Greedy:** greedy-choice property proven or cited?
- **Divide & conquer:** recurrence justified?

### 6. Architecture placement (R2)

- Domain: policy (what to optimize)
- Adapter: DS library, index configuration
- Flag leaks if DS details dominate use case

### 7. Anti-pattern scan (V.9)

Checklist:

- [ ] No O(n²) on large n without justification
- [ ] Correct graph algorithm for edge weights
- [ ] Right DS for query type (hash vs tree vs index)
- [ ] No exponential brute force on large inputs

### 8. S3c flag

If hot path is in the production code path → mark for Implement complexity review.

Proceed to [03-output.md](03-output.md).
