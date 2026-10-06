---
name: pbe-review-with-patterns
description: >-
  PR review using shared pattern vocabulary — catalog IDs and GoF names. Use at
  Implement review with @pr-reviewer and S1. Invoke with @pbe-review-with-patterns.
---

# S6 — PBE Review with Patterns

**ADLC5 stage:** Implement
**Skill ID:** S6  
**OKF catalog:** cite ids from [patterns/index.md](../../shared/docs/patterns/index.md) — do not dump cards  
**Knowledge base:** [Part I §I.6 Communicate design with patterns](../../shared/docs/knowledge-base/01-pbe.md)  
**Rules:** R0, R1 `pbe-consumption.mdc`  
**Playbook:** Part I §I.6, Part VI §VI.3 (critical distinctions — density not count)

### Catalog load (hard rules)

- Use claimed pattern **ids** from S5/S3 docs or `./scripts/adlc5 patterns lookup --id …`.
- Open a concept card **only** when fit is disputed (≤3); never attach the catalog to the PR pack.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Verify implementation aligns with claimed pattern structure using shared vocabulary. S6 complements S1 (smells) and S2 (layers)—it checks roles, collaborations, and variability points.

## When to invoke

- PR review where design intent should be verified against pattern vocabulary
- Implement review after Plan pattern selection (S5) or design advisory (S3)
- Checking refactor toward documented target patterns
- Companion to `@pr-reviewer` and S1 (not a replacement)

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Claimed patterns, S5/S3 docs |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Roles, fit, density |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Verdict, PR vocabulary |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Load context** — Design doc, S5 output, or PR description for claimed patterns.
2. **Name patterns in review** — Use OKF concept ids (`gof/strategy`, `algorithms/sorting`) or GoF names; lookup if needed — do not paste catalog indexes.
3. **Verify fit** — Does code structure match the named pattern's roles and variability points?
4. **Density check** — Patterns work in combination; flag gratuitous or missing integration.
5. **Refactor target** — If drift, describe target state using pattern vocabulary (stepwise, not big-bang).
6. **Cross-link reviews** — Layer issues → S2; smells → S1; hot-path O(·) → S3c.
7. **Avoid antipatterns** — "Singleton counting," pattern name without structure, catalog without ROI.

## Verdict definitions

| Verdict | Meaning |
|---------|---------|
| **aligned** | Roles and collaborations match claimed patterns |
| **partial** | Pattern intent present; structural drift fixable incrementally |
| **misaligned** | Wrong pattern or missing roles; refactor plan needed |

## Pattern fit checklist

For each claimed pattern:

- [ ] Context role identifiable in code
- [ ] Variation encapsulated (not switch explosion)
- [ ] Clients depend on abstraction (program to interfaces)
- [ ] Variability points match S5/S7 spec if cataloged

## Integration with ADLC5

```
Plan S5/S3 → Implement: S6 + S1 + S3c + @pr-reviewer
```

Use pattern names in PR comments so reviewers share vocabulary (PBE consumption guideline).

## Output format

```markdown
## Pattern Review — [PR / scope]

**Verdict:** aligned | partial | misaligned

### Claimed vs observed
| Pattern (catalog / GoF) | Claimed role | Observed in code | Match? |
|-------------------------|--------------|------------------|--------|

### Findings
| Severity | Pattern topic | Location | Recommendation |
|----------|---------------|----------|----------------|

### Target state (if refactor needed)
…

### Vocabulary for PR comment
> …
```

Reference: playbook Part I §I.6, Part VI §VI.3 (critical distinctions — density not count).

## Handoffs

| Issue | Skill |
|-------|-------|
| Layer leak | S2 |
| Smells in implementation | S1 |
| Wrong O(·) | S3c |
| Merge / thread resolution | @pr-reviewer |

## Anti-patterns

- Approving because PR mentions "Strategy" in description only
- Demanding catalog pattern when GoF ad hoc was agreed at S5
- Big-bang rewrite recommendation without stepwise target state

## Common misalignment patterns

| Claimed | Observed drift | Typical fix |
|---------|----------------|-------------|
| Strategy | `switch(type)` in Context | Extract interface; inject implementation |
| Repository | ORM entity in use case | Port + adapter mapping |
| Observer | Direct callback list mutation | Encapsulate subscribe/notify |
| Factory | `new Concrete()` in domain | Move creation to adapter/composition root |
| Facade | God class | Split by subsystem boundaries |

## PR comment vocabulary examples

Use explicit pattern role names:

- "Context should depend on `PricingStrategy`, not concrete `HolidayPricing`."
- "Catalog `transactional-outbox` Relay role missing—poller lives in controller."
- "Partial Observer fit: Subject notifies but Observer interface absent."

Shared vocabulary reduces review cycles (PBE §I.6).

## When S6 is N/A

Skip full S6 when PR is docs/config-only **and** no pattern claims in description.

Still run S1; run S3c if hot paths appear despite no pattern claims.
