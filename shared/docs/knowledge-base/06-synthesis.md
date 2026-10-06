## Part VI — Synthesis: five-layer agent stack

### VI.1 Decision flow (use case → delivery)

1. **Requirements** — Extract functional + **scale NFRs** (latency, throughput, data volume, memory). PBE: requirements-driven pattern selection.
2. **Architecture** — Clean Architecture: boundaries, dependency rule, screaming architecture. PBE: large-scope patterns first.
3. **Design** — HFDP: GoF pattern + OO principles for structure.
4. **Algorithm** — CLRS: if scale-sensitive, pick DS/algorithm; state O(·); use decision tables (Part V).
5. **Implement** — Clean Code: names, functions, tests, Boy Scout Rule.
6. **Org asset** — PBE: if recurrence + ROI, add to `shared/docs/patterns/` (spec + rule + skill/hook).

### VI.2 When to invoke each layer

| Layer | Invoke when |
|-------|-------------|
| PBE catalog | Recurring org workflow; codify after S8 ROI gate |
| Clean Architecture | New module, service, boundary, dependency review |
| HFDP | Structure choice, extensibility, communication in design |
| CLRS | Scale NFRs, hot paths, search/sort/graph/scheduling |
| Clean Code | Always during implement and review |

### VI.3 Critical distinctions

| Mistake | Reality |
|---------|---------|
| “Use all design patterns” | Pattern **density** = integration, not count |
| Strategy without complexity analysis | Strategy swaps **algorithms**—pick O(·) deliberately |
| Microservice = architecture | Boundaries **inside** services matter |
| Catalog every solution | PBE catalog only with **business impact** |
| Optimize everything | CLRS when scale justifies; else clarity |

### VI.4 Cross-reference matrix

| PBE guideline | Book ally |
|---------------|-----------|
| End-to-end pattern use | CA (all layers), CC (tests), CLRS (perf paths) |
| Piecemeal creation | CC case studies, PBE iterations |
| Simple solution space | HFDP (don't over-pattern), CLRS (stdlib first) |
| Refactor with patterns | CC stepwise + HFDP target + CA layers |
| Communicate with patterns | HFDP names in PRs + PBE catalog ids |

---

