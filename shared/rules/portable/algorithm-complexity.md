
# Algorithm Complexity (R5)

Apply when **scale NFRs** matter: large `n`, latency, throughput, or memory constraints.

## Core rules

- **State O(·)** on hot paths — Define input size `n`; document time/space for the chosen approach.
- **Document expected n** — "Sufficient for expected n" is valid for small-scale CRUD and glue code.
- **No premature optimization** — Prefer clarity and stdlib until scale justifies analysis.
- **Invest analysis when NFRs demand it** — Problems seldom announce which paradigm applies.

## Decision tables

Use `shared/docs/playbook.md` Part V (CLRS):

| Table | Section | Covers |
|-------|---------|--------|
| Sorting | V.4 | Merge, heap, quick, insertion, counting/radix |
| Search & lookup | V.5 | Hash, BST, binary search, heap, union-find |
| Graph | V.6 | BFS, DFS, MST, Dijkstra, Bellman-Ford, flow |
| Optimization | V.7 | DP, greedy, NP-completeness |
| String / text | V.8 | Naive, Rabin-Karp, KMP, platform index |

## Anti-patterns

- O(n²) nested loops on large `n` without justification
- Dijkstra with negative edge weights
- Greedy without greedy-choice proof
- Hash table when ordering or range queries required
- Micro-optimizing cold paths while hot path stays quadratic

## Cross-links

| CLRS | Link |
|------|------|
| HFDP Strategy | Algorithms are what strategies **swap** (R4) |
| Clean Architecture | Heavy algo in domain/use case; DS at policy boundary (R2) |

**Reference:** `shared/docs/playbook.md` Part V (CLRS) and Appendix F.
