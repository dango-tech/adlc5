## Part V — Introduction to Algorithms (CLRS)

*Source: Cormen, Leiserson, Rivest, Stein, MIT Press 2009 (1,313 pp.).*

### V.1 Core message

Algorithms lie at the heart of computing. **Efficiency is a design criterion** alongside correctness. Every algorithm should be understood with **running-time analysis**. Problems seldom announce which paradigm applies—invest analysis when **scale NFRs** justify it.

**Avoid premature optimization:** For small `n`, admin CRUD, or glue code—prefer clarity and stdlib; document “sufficient for expected n.”

### V.2 Foundations (Part I)

| Topic | Agent guidance |
|-------|----------------|
| Analyzing algorithms | Define input size `n`; state worst/average case |
| **O, Ω, Θ** | Big-O for upper bound; know common growth rates |
| Divide-and-conquer | Subproblems + combine cost; Master theorem |
| Randomized | Expected time when analysis simplifies design |

**Common complexities:** O(1), O(log n), O(n), O(n log n), O(n²), O(2^n) — know what dominates at your expected `n`.

### V.3 Design paradigms (Part IV — highest leverage)

| Paradigm | Use when | Caution |
|----------|----------|---------|
| **Dynamic programming** | Optimal substructure + **overlapping subproblems** | Memoize or tabulate |
| **Greedy** | **Greedy-choice property** holds (prove or cite) | Wrong greedy → wrong answer |
| **Divide-and-conquer** | Independent subproblems | Combine step can dominate |
| **Amortized** | Rare expensive ops in a sequence | Dynamic arrays, some heaps |

### V.4 Decision table — Sorting

| Situation | Prefer | Time | Notes |
|-----------|--------|------|-------|
| General comparison, stable | Merge sort | O(n log n) | Extra space |
| General, in-place | Heapsort | O(n log n) | Not stable |
| Average fast, in-place | Quicksort | O(n log n) avg | Worst O(n²); watch pivot |
| Small n or nearly sorted | Insertion sort | O(n²) worst | Often wins for tiny n |
| Integer keys in bounded range | Counting / radix | O(n+k) | Assumptions on keys |
| External / disk | B-tree based | — | Not in-memory sort |

### V.5 Decision table — Search and lookup

| Situation | Prefer | Average | Notes |
|-----------|--------|---------|-------|
| Static set, no order | Hash table | O(1) | Collision strategy |
| Ordered set, range queries | Balanced BST (e.g. red-black) | O(log n) | In-order traversal |
| Static sorted array | Binary search | O(log n) | No mutation |
| Priority / scheduling | Binary heap | O(log n) insert/extract | Not full sort |
| Frequent union-find | Disjoint-set forest | Nearly O(α(n)) | Connectivity, MST |

### V.6 Decision table — Graph problems

| Problem | Algorithm | When |
|---------|-----------|------|
| Unweighted shortest path | BFS | Layering, fewest edges |
| Cycle / topo sort / SCC | DFS | Dependencies, compile order |
| MST | Kruskal (union-find) or Prim (heap) | Sparse vs dense |
| SSSP, non-negative weights | Dijkstra | **No negative edges** |
| SSSP, negative weights | Bellman-Ford | Detect negative cycle |
| All-pairs | Floyd-Warshall | Dense, small V |
| Max flow / matching | Ford-Fulkerson family | Network capacity |

**Representation:** Adjacency list for sparse graphs; matrix for dense or all-pairs.

### V.7 Decision table — Optimization

| Situation | Approach |
|-----------|----------|
| Overlapping subproblems + optimal substructure | Dynamic programming |
| Greedy-choice proven | Greedy |
| Brute force exponential | Stop—check **NP-completeness**; use approximation/heuristic |
| Need optimal, small input | DP or specialized exact algo |

### V.8 Decision table — String / text

| Situation | Approach |
|-----------|----------|
| Single pattern, rare | Naive search |
| Multiple patterns / fingerprint | Rabin-Karp |
| Repeated same text | KMP / automata |
| Very large scale | Use platform index (Elasticsearch, etc.) + CLRS for in-process core |

### V.9 CLRS agent anti-patterns

- O(n²) nested loops on large `n` without justification
- Dijkstra with negative edge weights
- Greedy without greedy-choice proof
- Hash table when ordering or range queries required
- Exotic structures when hash map or array suffices
- Micro-optimizing cold paths while hot path stays quadratic
- Brute-force exponential on large inputs

### V.10 CLRS ↔ other books

| CLRS | Link |
|------|------|
| HFDP Strategy | Algorithms are what strategies **swap** |
| Clean Architecture | Heavy algo in domain/use case; DS at policy boundary |
| Clean Code | Clear code *wrapping* the right algo |
| PBE | Recurring “index/search/schedule at scale” → catalog pattern + skill |

---

