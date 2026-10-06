# S7 — Good vs Bad Pattern Specs

## Specification vs implementation

### Bad

50 lines of copied Java from exemplar in the spec file.

### Good

Role table + pointer: `services/billing/outbox/` — reference implementation.

---

## Variability points

### Bad

> "Configure as needed."

### Good

| Transport | polling / push webhook | polling — default for batch systems |

---

## Context

### Bad

> "Use everywhere."

### Good

Apply when DB commit and message publish must be atomic; **not** for read-only caches.

---

## Gate

### Bad

Author S7 spec without S8 approval.

### Good

`roi_notes: "S8 approved 2026-05-01 — defer rejected; 3 teams, 6 occurrences/year"`
