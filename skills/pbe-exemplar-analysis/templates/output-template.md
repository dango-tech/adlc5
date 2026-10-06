# Exemplar Analysis — [candidate / path]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Catalog (Production — discovery)

---

## Exemplars reviewed

| Path | Quality | Notes |
|------|---------|-------|
| `services/billing/outbox/` | high | tested, clear adapter split |

---

## Problem (abstracted)

Ensure side effects publish reliably after transactional state change without dual-write inconsistency.

---

## Forces

- Atomicity with DB commit
- At-least-once delivery tolerance
- Testability without message broker in unit tests

---

## Structure

| Role | Exemplar type/module | Responsibility |
|------|---------------------|----------------|
| OutboxStore | `OutboxRepository` | Persist pending events |
| Relay | `OutboxPoller` | Publish and mark sent |
| Handler | `OrderPlacedHandler` | Write business + outbox row |

---

## Collaboration diagram

```
UseCase → OutboxStore.append(event)
Relay → OutboxStore.fetchPending() → MessageBus.publish()
```

---

## Variability points

| Point | Exemplar A (billing) | Exemplar B (campaigns) | Exemplar C (auth) |
|-------|----------------------|------------------------|-------------------|
| Transport | polling | polling | webhook |

---

## Proposed pattern name / id

**id:** `transactional-outbox`  
**name:** Transactional Outbox

---

## GoF alignment

Related to Message Channel / Pipes-and-Filters (integration); not classic GoF—document as org pattern.

---

## Gaps & cautions

Webhook variant in auth not fully tested; spec should note polling as default MVP.

---

## Ready for S7

- [x] Yes — sufficient abstraction
- [ ] No — need additional exemplar
