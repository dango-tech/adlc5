---
name: design-pattern-advisor
description: >-
  HFDP GoF pattern selection using seven OO principles and playbook decision
  tables. Use during Plan for structural design problems. Invoke with
  @design-pattern-advisor.
---

# S3 — Design Pattern Advisor

**ADLC5 stage:** Engineer  
**Skill ID:** S3  
**OKF catalog:** [shared/docs/patterns/index.md](../../shared/docs/patterns/index.md) → `gof/` (concept id e.g. `gof/strategy`)  
**Knowledge base (deep, on demand):** [Part IV — Head First Design Patterns](../../shared/docs/knowledge-base/04-design-patterns.md)  
**Rules:** R4 `oo-design-principles.mdc`  
**Playbook:** Part IV §IV.2–IV.4 (principles, GoF tables)

### Catalog load (hard rules)

- Default: `patterns/index.md` or `gof/index.md` only — never paste the full catalog.
- Lookup: `./scripts/adlc5 patterns lookup --tags … --group gof` (ids/paths only).
- Open **at most 1–3** matching `gof/<slug>.md` cards; KB Part IV **only if** cards are insufficient.
- Cite concept **ids** in output; do not embed card bodies in Build packs.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Recommend GoF design patterns grounded in problem forces—not pattern shopping. S3 applies HFDP seven principles and playbook decision tables to structural design questions during Plan.

## When to invoke

- Choosing structure for extensibility, variation, or communication
- Replacing large switch/if-else chains or subclass explosions
- Design review before interfaces or class diagrams
- Pair with S3b when Strategy swaps algorithms at scale
- Narrow structural sub-problem (use S5 for full requirements-driven stack)

**Do not invoke for:** org catalog authoring (S7), ROI gate (S8), or line-level code review (S1).

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Problem statement, variation, constraints |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Seven principles, GoF table match |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Recommendation, alternatives, handoffs |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **State the problem** — Behavior that varies, coupling pain, or extension need (not "pick a pattern").
2. **Apply seven principles** — Encapsulate variation; composition over inheritance; program to interfaces; loose coupling; OCP; Law of Demeter; SRP.
3. **Load OKF cards** — Lookup then open ≤3 matching `gof/<slug>.md` cards (index → group index → cards). Never glob the catalog.
4. **Match forces** — Use card "When" / "Often confused with"; fall back to KB Part IV §IV.3–IV.4 only if cards are insufficient.
5. **Name 1–2 candidates** — Primary pattern + alternative rejected with rationale; cite concept ids (`gof/strategy`).
6. **Variability points** — What changes vs what stays stable; interface sketch if helpful.
7. **Density check** — Complementary patterns in combination; avoid pattern shopping.
8. **Catalog discipline** — Community GoF seeds are reference cards; org-specific assets still need Rule of Three + S8.
9. **Handoff** — If scale NFRs apply, recommend `@algorithm-advisor` (S3b) for Strategy internals.

## Seven OO principles (HFDP)

| Principle | Design question |
|-----------|-----------------|
| Encapsulate what varies | What changes independently? |
| Favor composition over inheritance | Is "is-a" forcing fragile hierarchies? |
| Program to interfaces | Can clients depend on abstractions? |
| Strive for loosely coupled designs | Who knows about whom? |
| Open for extension, closed for modification | Will new types require editing stable code? |
| Law of Demeter | Only talk to immediate friends |
| Single responsibility | One reason to change per class? |

## GoF quick reference

| Problem | Pattern |
|---------|---------|
| Interchangeable algorithms | Strategy |
| One-to-many notification | Observer |
| Runtime behavior extension | Decorator |
| Object creation scattered | Factory Method / Abstract Factory |
| Tree part-whole | Composite |
| Mode-dependent behavior | State |
| Legacy interface mismatch | Adapter |
| Subsystem simplification | Facade |

Full table: playbook Part IV §IV.3.

## Often confused pairs

| Pair | Distinction |
|------|-------------|
| Strategy vs State | Strategy swaps algorithms; State swaps behavior by internal mode |
| Decorator vs Strategy | Decorator wraps and adds responsibility; Strategy replaces core algorithm |
| Factory Method vs Abstract Factory | FM: one product line; AF: families of related products |
| Adapter vs Facade | Adapter translates one interface; Facade simplifies a subsystem |

## Integration with ADLC5

```
Engineer: S2 (boundaries) → S3 (design) → S3b (algorithms if scale) → S5 (full stack)
```

- Run S3 after S2 when architectural boundaries are clear.
- S5 invokes S3 logic for gaps not in org catalog.
- S6 verifies pattern fit during Implement review.

## Output format

```markdown
## Design Pattern Advisory — [problem summary]

### Problem & forces
- …

### Recommended pattern(s)
| Pattern | Role | Why |
|---------|------|-----|

### Rejected alternatives
- …

### Variability points
- …

### Interfaces (optional sketch)
…

### Next steps
- [ ] S3b if scale-sensitive Strategy
- [ ] S2 if architectural boundaries unclear
```

Reference: playbook Part IV §IV.2 (principles), §IV.3–IV.4 (GoF tables).

## Anti-patterns

- Naming a pattern before stating forces
- Singleton as default global state
- Pattern density without integration (isolated Observer + Strategy with no collaboration)
- Cataloging before Rule of Three (defer to S4/S8)
