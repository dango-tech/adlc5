# Business Impact Assessment — [candidate id]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Catalog (gate)

---

## Summary

**Decision:** approve | defer | reject

[One-sentence rationale]

---

## Evidence (Rule of Three)

| # | Context | Reference |
|---|---------|-----------|
| 1 | billing service | PR-101 |
| 2 | campaigns | PR-204 |
| 3 | auth | path |

---

## ROI estimate

| Factor | Estimate |
|--------|----------|
| Expected annual occurrences | 6 |
| Hours saved per occurrence | 4 |
| Production cost (spec + impl + maint, year 1) | 40h |
| Net ROI | (6×4×teams) − 40h = … [ASSUMPTION: 3 teams] |

---

## Qualitative benefits

- Shared vocabulary in PR review (S6)
- Reduced outbox implementation defects

---

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Perfect Pattern | S9 MVP skill only; defer codegen |

---

## Next step

- [ ] S7 pattern description
- [ ] S10 exemplar analysis
- [ ] S9 piecemeal implementation
- [ ] None — use GoF ad hoc
