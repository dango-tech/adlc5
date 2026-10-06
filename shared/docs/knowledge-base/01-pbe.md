## Part I — Patterns-Based Engineering (PBE)

*Source: Ackerman & Gonzalez, Pearson 2010.*

### I.1 Definition

> PBE is a systematic, disciplined, and quantifiable approach to software development that leverages **pattern specifications** and **pattern implementations** throughout the software development and delivery process.

PBE is a **practice component** (like testing or SCM), not a replacement for Scrum/XP/OpenUP. It extends **Asset-Based Development (ABD)** by specializing in **patterns** as the primary reusable asset type.

### I.2 Core concepts

| Term | Meaning |
|------|---------|
| **Pattern** | Proven best-practice solution to a recurring problem in a given context |
| **Asset** | Artifacts + usage instructions + **variability points** |
| **Exemplar** | Reference solution used to discover a pattern (patterns are discovered, not invented) |
| **Rule of Three** | Same problem/solution in three unique situations → candidate pattern |
| **Specification** | Document: context, problem, forces, solution, consequences |
| **Implementation** | Automation: wizard, M2M/M2T, UML template, scaffold, hook |

| | Specification | Implementation |
|--|---------------|----------------|
| Value | Vocabulary, teaching, reviews | Productivity, consistency, governance |
| Risk | Manual drift | Upfront cost; must be tested |

**Implementation types:** UML/intra-model; model-to-model; model-to-text (codegen).

### I.3 PBE core values

1. **Patterns in combination** — dense, integrated use; not isolated micro-patterns.
2. **Always identify and build new patterns** — organizational patterns matter.
3. **Build and use on the same project** — no “harvest only at the end.”
4. **Patterns are alive** — iterative releases; feedback drives versions.
5. **Focus on consumability** — findable, usable, documented.
6. **Fits many processes** — augments existing SDLC.

### I.4 Lifecycle (ABD-aligned)

| Activity | Intent |
|----------|--------|
| **Identification** | Pattern opportunity each iteration; Rule of Three |
| **Production** | Spec + implementation; exemplar analysis; testing |
| **Management** | Repository, versioning, metadata, review |
| **Consumption** | Design, generate, refactor, reverse-engineer |

### I.5 Foundational PBE patterns (meta)

| Pattern | Essence |
|---------|---------|
| End-to-End Pattern Use | Patterns across requirements → deploy → maintain |
| Piecemeal Pattern Creation | Ship 80% value early; expand per iteration |
| Simple Solution Space | Fewer valid choices → easier consumption |
| Single Pattern – Varied Use Cases | One pattern, many contexts via variability points |

### I.6 Consumption guidelines

| Guideline | Essence |
|-----------|---------|
| Communicate design with patterns | Shared names in PRs and reviews |
| Design solutions with patterns | Patterns as design constructs |
| Pattern density | Tight integration; not Singleton counting |
| Pattern selection driven by requirements | Requirements ↔ patterns via metadata |
| Refactor with patterns | Patterns = target state |
| Select large-scope patterns first | Architecture → design → idioms |
| Use an asset repository | Searchable catalog |
| Use pattern definitions to understand legacy | Reverse-engineer via vocabulary |
| Use patterns to find patterns | One pattern reveals others |

### I.7 PBE antipatterns

| Antipattern | Mitigation |
|-------------|------------|
| Perfect Pattern | Piecemeal creation |
| Generic DSL | Domain-specific languages |
| Waterfall pattern use | Identify each iteration |
| Get ’em next time | Build during current project |
| Patterns everywhere | Business impact + density discipline |

### I.8 Documented benefits

Productivity, quality, communication, expertise leverage, governance, distributed-team alignment.

### I.9 PBE ↔ other books

| PBE | Cross-link |
|-----|------------|
| Select large-scope first | Clean Architecture layers |
| Refactor with patterns | Clean Code stepwise refactors + HFDP target |
| Pattern density | HFDP composition; CA boundary density |
| Determine business impact | When to add `shared/docs/patterns/` vs use GoF ad hoc |
| Pattern implementations | Cursor hooks + skills |

---

