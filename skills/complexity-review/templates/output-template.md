# Complexity Review — [scope / PR]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Implement
**Verdict:** pass | pass-with-notes | fail | N/A

---

## S3b reference

| Field | Value |
|-------|-------|
| S3b status | advisory / N/A / missing |
| Documented O(·) | |
| Expected n | |

---

## Hot paths

| Path | Location | Stated O(·) | Observed O(·) | Expected n | Assessment |
|------|----------|-------------|---------------|------------|------------|
| Batch enrich | `svc.ts:40-55` | O(n) | O(n²) | 10⁴ | **fail** |

---

## Anti-pattern hits

| ID | Issue | Location | Fix |
|----|-------|----------|-----|
| AP1 | Nested loop on orders × items | `svc.ts:44` | Index items by orderId |

---

## Missing documentation

- Code spec lacks O(·) for `enrichOrders`

---

## Recommendations

1. Replace nested loop with map lookup — O(n)
