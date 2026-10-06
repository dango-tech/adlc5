# S8 — Good vs Bad ROI Assessment

## Evidence

### Bad

> "Everyone wants this pattern."

No Rule of Three table.

### Good

Three contexts with ticket/PR/path references; independent verification.

---

## ROI math

### Bad

> "ROI is positive."

No factors shown.

### Good

| Expected annual occurrences | 6 [ASSUMPTION: 2/quarter] |
| Hours saved | 4h — avoid re-designing outbox |
| Production cost | 32h S7+S9+MVP |

---

## Decision

### Bad

**approve** because pattern is "best practice."

### Good

**reject** — stdlib + GoF Observer sufficient; recurrence forecast 1/year < production cost.

---

## Defer

### Bad

Defer forever without evidence plan.

### Good

**defer** — 2/3 contexts; revisit after Q3 campaign service ships.
