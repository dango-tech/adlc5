# S10 — Good vs Bad Exemplar Analysis

## Abstraction

### Bad

> "CampaignOutboxPattern applies to campaigns."

Domain noun baked into pattern name.

### Good

> **transactional-outbox** — publish reliably after DB commit; exemplars: billing, campaigns, auth.

---

## Roles

### Bad

> "See `OutboxService.java` line 42."

Line reference without role name.

### Good

| Relay | `OutboxPoller` | Fetch pending, publish, mark sent |

---

## Code in spec

### Bad

Paste 30 lines of exemplar into analysis for S7 to copy.

### Good

Collaboration diagram + path pointer; structure only.

---

## Variability

### Bad

Single exemplar → claim three variability columns filled with "TBD."

### Good

**Ready for S7: No** — need campaigns exemplar before variability table complete.

---

## R2 alignment

### Bad

Ignore that exemplar puts SQL in use case.

### Good

**Gap:** `CreateOrderUseCase` embeds SQL — S7 should recommend port extraction; exemplar not ideal but fix documented.
