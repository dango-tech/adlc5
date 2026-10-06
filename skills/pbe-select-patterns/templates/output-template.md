# Pattern Selection — [feature / use case]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Engineer

---

## Requirements ↔ patterns

| Requirement | NFR tags | Pattern(s) | Source (catalog / GoF) |
|-------------|----------|------------|------------------------|
| R1: Plugin pricing | extensibility | Strategy | GoF |
| R2: Persist orders | — | Repository port | catalog: `repo-port` |

---

## Layer stack (inside → out)

1. **Architecture:** Use case `PlaceOrder`; `OrderRepository` port (S2)
2. **Design:** Strategy for pricing rules (S3)
3. **Algorithm:** O(log n) price tier lookup (S3b)

---

## Catalog usage

- **Applied:** `repo-port`
- **GoF ad hoc:** Strategy

---

## Density notes

Repository port isolates persistence; Strategy variants injected via Factory at adapter boundary.

---

## Handoffs

- [ ] S2 — complete
- [ ] S3b — price tier lookup advisory attached
- [ ] S8 — not required (GoF ad hoc sufficient)
