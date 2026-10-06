# Pattern Review — [PR / scope]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Implement
**Verdict:** aligned | partial | misaligned

---

## Claimed vs observed

| Pattern (catalog / GoF) | Claimed role | Observed in code | Match? |
|-------------------------|--------------|------------------|--------|
| Strategy | Pricing variation | `switch` on type in `Checkout` | partial |

---

## Findings

| Severity | Pattern topic | Location | Recommendation |
|----------|---------------|----------|----------------|
| major | Strategy | `Checkout.ts:88` | Introduce `PricingStrategy` interface |

---

## Target state (if refactor needed)

1. Extract `PricingStrategy` port
2. Move concrete algorithms to adapter package
3. Inject strategy via Factory at composition root

---

## Vocabulary for PR comment

> **S6:** partial — Strategy intent documented in S5 but Context uses type switch; align with interface-based Strategy (HFDP).
