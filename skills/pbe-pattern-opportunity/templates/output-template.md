# Pattern Opportunity Scan — [scope]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Spec / Engineer

---

## Candidates

| ID | Problem (context-free) | Occurrences | Evidence | Scope |
|----|------------------------|-------------|----------|-------|
| outbox-relay | Reliable event publish after DB commit | 3 | PR-101, PR-204, svc-b | architectural |

---

## Rule of Three status

| Candidate | Count | Unique contexts | Meets Rule of Three? |
|-----------|-------|-----------------|----------------------|
| outbox-relay | 3 | billing, campaigns, auth | yes |

---

## Recommended actions

| Candidate | Action |
|-----------|--------|
| outbox-relay | Proceed to S8 |

---

## Exemplars for S10

- `services/billing/outbox/` — clearest implementation
- `services/campaigns/events/` — variant with polling adapter
