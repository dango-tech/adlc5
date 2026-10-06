---
name: algorithm-advisor
description: >-
  CLRS algorithm and data-structure selection using playbook decision tables
  and scale NFRs. Use during Plan when latency, throughput, or volume
  matter. Invoke with @algorithm-advisor.
---

# S3b — Algorithm Advisor

**ADLC5 stage:** Engineer  
**Skill ID:** S3b  
**OKF catalog:** [shared/docs/patterns/index.md](../../shared/docs/patterns/index.md) → `algorithms/` (concept id e.g. `algorithms/sorting`)  
**Knowledge base (deep, on demand):** [Part V — Introduction to Algorithms (CLRS)](../../shared/docs/knowledge-base/05-algorithms-clrs.md)  
**Rules:** R5 `algorithm-complexity.mdc`  
**Playbook:** Part V §V.1–V.9 (foundations, tables, anti-patterns)

### Catalog load (hard rules)

- Default: `patterns/index.md` or `algorithms/index.md` only — never paste the full catalog.
- Lookup: `./scripts/adlc5 patterns lookup --tags … --group algorithms` (ids/paths only).
- Open **at most 1–3** matching `algorithms/<slug>.md` cards; KB Part V **only if** cards are insufficient.
- Cite concept **ids** in output; do not attach catalog to Build packs unless the story names an algorithm class.

## Purpose


### Model recommendation

**Tier:** reasoning. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Select algorithms and data structures with explicit O(·) justification tied to scale NFRs. S3b complements S3 Strategy internals and S2 domain placement—algorithms are policy; DS details belong at boundaries when possible.

## When to invoke

- Scale NFRs documented: expected `n`, latency, throughput, memory
- Search, sort, graph, scheduling, or optimization design
- Strategy pattern needs concrete algorithm choice
- Before implementing hot paths in `@adlc5-plan` code specs

**Skip when:** small `n`, admin CRUD, glue code — document "sufficient for expected n" instead.

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | NFRs, n, problem class |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Decision tables, O(·), rejection |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Recommendation, S3c flag |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Capture NFRs** — Define input size `n`, worst/average case needs, memory budget.
2. **Classify problem** — Sort, search/lookup, graph, optimization, string/text.
3. **Load OKF decision card** — Lookup then open ≤3 matching `algorithms/<slug>.md` cards (never the full catalog or KB essay first).
4. **Select from decision table** — Prefer stdlib/platform when sufficient; cite concept id.
5. **State O(·)** — Time and space for chosen approach; note dominant term at expected `n`.
6. **Reject alternatives** — Why simpler or faster options were ruled out.
7. **Paradigm check** — Load `algorithms/dynamic-programming`, `greedy`, or `divide-and-conquer` when relevant.
8. **Architecture placement** — Heavy logic in domain/use case; DS details at policy boundary (R2).
9. **Anti-patterns** — Check [algorithms/anti-patterns.md](../../shared/docs/patterns/algorithms/anti-patterns.md); KB §V.9 only if needed.

## Decision table index (OKF concept ids)

| Domain | Concept id | KB fallback |
|--------|------------|-------------|
| Sorting | `algorithms/sorting` | V.4 |
| Search & lookup | `algorithms/search-lookup` | V.5 |
| Graph | `algorithms/graph` | V.6 |
| Optimization | `algorithms/optimization` | V.7 |
| String / text | `algorithms/string-text` | V.8 |
| Anti-patterns | `algorithms/anti-patterns` | V.9 |

## Complexity notation reminder

| Symbol | Meaning |
|--------|---------|
| O(f(n)) | Upper bound (worst-case typical reporting) |
| Ω(f(n)) | Lower bound |
| Θ(f(n)) | Tight bound when proven |

State both **time** and **space** for the recommendation.

## Integration with ADLC5

```
Plan: S3b → Tasks code spec documents O(·) → Implement: S3c verifies implementation
```

- Every S3b advisory on a hot path must flag S3c during Implement review.
- If no scale NFRs, output N/A template—do not over-engineer.

## Output format

```markdown
## Algorithm Advisory — [use case]

### Scale NFRs
- n ≈ …; latency …; memory …

### Recommendation
| Algorithm / DS | Time | Space | Notes |
|----------------|------|-------|-------|

### Alternatives rejected
| Option | Why not |
|--------|---------|

### Expected n justification
…

### Implementation notes
- Layer placement: …
- Platform/stdlib option: …

### Complexity review flag
- [ ] Hot path → schedule S3c during Implement review
```

Reference: playbook Part V §V.1–V.3 (foundations), §V.4–V.9 (tables and anti-patterns).

## When to output N/A

```markdown
## Algorithm Advisory — [use case]

**Status:** N/A — sufficient for expected n (n < [threshold]); admin CRUD / glue code. No hot-path review required.
```

Document assumed n even for N/A.

## Handoffs

| Condition | Route |
|-----------|-------|
| Wrong problem class (need pattern not algo) | S3 |
| Layer placement unclear | S2 |
| Implementation verification | S3c during Implement |

## Anti-patterns

- Premature micro-optimization on cold paths
- Custom sort when stdlib O(n log n) suffices
- Greedy without proving greedy-choice property
- Hiding O(n²) nested loops behind "small n" without measurement
