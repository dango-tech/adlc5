---
name: clean-architecture-review
description: >-
  Clean Architecture review — dependency rule, layer leaks, screaming architecture.
  Use during Plan before implementation or when reviewing module boundaries.
  Invoke with @clean-architecture-review.
---

# S2 — Clean Architecture Review

**ADLC5 stage:** Plan (architecture before Implement)
**Skill ID:** S2  
**OKF catalog:** [patterns/architecture/](../../shared/docs/patterns/architecture/index.md) — ≤3 cards  
**Knowledge base:** [Part III — Clean Architecture](../../shared/docs/knowledge-base/03-clean-architecture.md)  
**Rules:** R2 `clean-architecture.mdc`  
**Playbook:** Part III §III.2–III.4 (SOLID, components, CA)

### Catalog load (hard rules)

- Lookup: `./scripts/adlc5 patterns lookup --group architecture --tags …` (ids/paths).
- Open **≤3** `architecture/*` cards; KB Part III **only if** cards are insufficient.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Verify that module boundaries respect the dependency rule and that the structure "screams" use cases—not frameworks. S2 runs during Plan and may be repeated during Implement when architectural drift is suspected.

## When to invoke

- New module, service, or bounded context design
- Pre-implementation architecture gate during `@adlc5-plan`
- PR review when layer violations or framework leakage suspected
- Refactoring package/folder layout
- Before `@adlc5-plan` Phase 1 design when boundaries are unclear

**Do not invoke for:** line-level smells (S1), GoF pattern choice (S3), or algorithm selection (S3b).

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Scope, layer hypothesis, requirements |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Dependency rule, leaks, SOLID at scale |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Layer map, violations, gate checklist |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Identify layers** — Map Entities → Use Cases → Adapters → Frameworks/Drivers for the scope.
2. **Dependency rule** — Verify source dependencies point **inward**; inner circles must not import outer.
3. **Layer leaks** — Flag ORM entities, SQL, HTTP DTOs, or framework types in use cases/domain.
4. **Screaming architecture** — Folder/package names should reflect use cases, not framework tech.
5. **SOLID at module scale** — SRP per module; DIP via ports/adapters; ISP on interfaces.
6. **Component principles** — Check for cycles (ADP), stability direction (SDP), abstract stable cores (SAP).
7. **Humble Object** — Hard-to-test edges (UI, DB, I/O) behind boundaries; core logic unit-testable.
8. **Tests** — Outermost ring; unit tests should not require GUI/DB when avoidable.

## Layer reference

| Layer | Contains | Must NOT depend on |
|-------|----------|-------------------|
| **Entities** | Enterprise business rules | Use cases, UI, DB, frameworks |
| **Use cases** | Application-specific rules | Frameworks, DB drivers, HTTP |
| **Interface adapters** | Controllers, presenters, gateways | Framework internals in domain |
| **Frameworks & drivers** | DB, web, devices | — (outermost) |

## Common violations

| Severity | Violation | Example |
|----------|-----------|---------|
| high | ORM entity in use case | `@Entity` class imported in `CreateOrderUseCase` |
| high | SQL in domain | Raw query string in entity method |
| medium | HTTP DTO in use case | `Express.Request` in application service |
| medium | Framework folder layout | `controllers/` only; no `place_order/` |
| low | Fat adapter | Controller contains business rules |

## Integration with ADLC5

```
Specify → Plan (S2 + S3/S5 + S3b) → Tasks → Implement
```

- S2 gate should pass before Plan design is finalized.
- S5 pattern selection assumes S2 boundaries are clear—or S2 is invoked from S5 handoff.
- During Implement, re-run S2 if the PR introduces cross-layer imports.

## Output format

```markdown
## Clean Architecture Review — [scope]

**Verdict:** pass | pass-with-notes | fail

### Layer map
| Layer | Modules / packages | Notes |
|-------|-------------------|-------|

### Violations
| Severity | Rule | Location | Fix |
|----------|------|----------|-----|
| high | Dependency inward | `path` | Move … to adapter |

### Boundaries recommended
- …

### Dependency diagram (optional)
[mermaid or ASCII inward flow]

### Gate
- [ ] Dependency rule satisfied
- [ ] No framework/DB in use cases
- [ ] Screaming architecture
- [ ] Testability (Humble Object)
```

Reference playbook Part III §III.4 (Clean Architecture) and §III.2–III.3 (SOLID, components).

## Verdict criteria

| Verdict | Criteria |
|---------|----------|
| **pass** | Dependency rule holds; no high-severity leaks |
| **pass-with-notes** | Medium issues with clear remediation plan |
| **fail** | High-severity inward violations or untestable core |

## Handoffs

| Finding | Route to |
|---------|----------|
| Structural pattern needed | S3 `@design-pattern-advisor` |
| Port/adapter sketch | S5 `@pbe-select-patterns` |
| Line-level smells in adapters | S1 `@craftsmanship-code-review` |
| Scale-sensitive domain logic | S3b `@algorithm-advisor` |

## Anti-patterns for reviewers

- Demanding perfect CA on legacy modules without migration path
- Ignoring screaming architecture because "it's a small service"
- Treating DTOs as entities without boundary mapping
