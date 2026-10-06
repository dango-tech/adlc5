# Design Pattern Advisory — [problem summary]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Engineer

---

## Problem & forces

- [Behavior that varies]
- [Quality attributes at stake]

---

## Recommended pattern(s)

| Pattern | Role | Why |
|---------|------|-----|
| Strategy | Encapsulate pricing algorithms | Eliminates switch on promo type; OCP for new promos |

---

## Rejected alternatives

- **State** — variation is algorithm choice at runtime, not mode transitions within object lifecycle

---

## Variability points

| Fixed | Varies |
|-------|--------|
| Checkout context | Pricing algorithm implementation |

---

## Interfaces (optional)

```
interface PricingStrategy { Money total(Order order); }
class Checkout { PricingStrategy strategy; }
```

---

## Next steps

- [ ] S3b — [if scale NFRs]
- [ ] S2 — [if boundaries unclear]
