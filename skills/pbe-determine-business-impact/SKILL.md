---
name: pbe-determine-business-impact
description: >-
  ROI gate before adding patterns to org catalog — quantify recurrence, cost,
  and savings. Use at Catalog stage after S4 candidate identification. Invoke
  with @pbe-determine-business-impact.
---

# S8 — PBE Determine Business Impact

**ADLC5 stage:** Catalog (gate before Production)  
**Skill ID:** S8  
**Knowledge base:** [Part I §I.7 antipatterns + Part VIII gap matrix](../../shared/docs/knowledge-base/01-pbe.md)  
**Rules:** R0 `pbe-core-values.mdc`  
**Playbook:** Part I §I.7 (Patterns everywhere → business impact), Part VI §VI.3

Do not dump OKF catalog during ROI — work from the candidate evidence table; open ≤1 catalog card only if comparing to an existing id.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Quantify whether an org pattern asset earns its production and maintenance cost. S8 is the mandatory gate before S7/S9—failed gate means GoF ad hoc consumption via S3/S5.

## When to invoke

- Before authoring S7 pattern spec or S9 implementation
- After S4 identifies Rule of Three candidate
- Quarterly catalog hygiene — deprecate low-ROI entries
- User asks "is this worth cataloging?"

**Default:** Use GoF/community patterns ad hoc when gate fails.

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | S4 candidate, evidence |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | ROI, risks, decision |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Decision record for S7 |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Restate candidate** — Problem, solution shape, S4 evidence (three contexts).
2. **Recurrence forecast** — How often will teams hit this in next 12 months?
3. **Cost to produce** — Spec (S7), exemplar (S10), skill/rule/hook (S9), maintenance.
4. **Cost without pattern** — Repeated design time, defects, inconsistency, review churn.
5. **Quantify ROI** — Simple estimate: `(occurrences × hours saved) − production cost`; qualitative factors OK if numbers unavailable.
6. **Risk** — Perfect Pattern antipattern; stale implementation; wrong abstraction level.
7. **Decision** — Approve catalog | defer (need more evidence) | reject (GoF ad hoc sufficient).
8. **Record** — `roi_notes` in pattern metadata for S7.

## ROI formula (simple)

```
Net ROI ≈ (expected_annual_occurrences × hours_saved_per_occurrence) − production_cost_annualized
```

Document assumptions explicitly when data is sparse.

## Decision matrix

| Decision | Criteria |
|----------|----------|
| **approve** | Rule of Three met + positive or strategic ROI |
| **defer** | Promising but <3 contexts or weak forecast |
| **reject** | GoF/stdlib sufficient; low recurrence; cost > savings |

## Integration with ADLC5

```
S4 (candidate) → S8 (gate) → S10 → S7 → S9
                     ↓ reject
                 S3/S5 GoF ad hoc
```

No catalog entries without passing this gate (playbook Part XI §XI.3 habit 7).

## Output format

```markdown
## Business Impact Assessment — [candidate id]

### Summary
**Decision:** approve | defer | reject

### Evidence (Rule of Three)
| # | Context | Reference |
|---|---------|-----------|

### ROI estimate
| Factor | Estimate |
|--------|----------|
| Expected annual occurrences | … |
| Hours saved per occurrence | … |
| Production cost (spec + impl + maint) | … |
| Net ROI | … |

### Qualitative benefits
- Communication, governance, quality, …

### Risks & mitigations
…

### Next step
- [ ] S7 pattern description
- [ ] S10 exemplar analysis
- [ ] S9 piecemeal implementation
- [ ] None — use GoF ad hoc
```

Reference: playbook Part I §I.7 (Patterns everywhere → business impact), Part VI §VI.3 (catalog only with business impact).

## Catalog hygiene

Re-run S8 for existing patterns when:

- Zero consumption in 12 months
- Implementation stale vs exemplars
- Maintenance cost exceeds documented savings

## Anti-patterns

| Antipattern | S8 response |
|-------------|-------------|
| Patterns everywhere | reject or defer |
| Perfect Pattern | approve with S9 MVP scope cap |
| Political cataloging | require evidence table |
