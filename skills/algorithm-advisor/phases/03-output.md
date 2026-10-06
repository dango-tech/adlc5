---
name: output
description: Phase 3 — Output for S3b. Deliver algorithm recommendation or N/A status.
---

# Phase 3: Output — Algorithm Advisor

## Purpose

Record algorithm choice in design artifacts for Build and S3c verification.

## Output paths

### Full advisory

Use when scale NFRs apply. Complete [../templates/output-template.md](../templates/output-template.md).

Required sections:

- Scale NFRs
- Recommendation table (Algorithm/DS, Time, Space, Notes)
- Alternatives rejected
- Expected n justification
- Implementation notes (layer, stdlib)
- Complexity review flag checkbox

### N/A advisory

When n is bounded and operation is cold path:

```markdown
**Status:** N/A — sufficient for expected n
**Assumed n:** …
**Rationale:** …
```

Still document assumed n for audit trail.

## Delivery handoff

Copy recommendation into code spec:

- Function/module owning hot path
- Stated O(·) in comment or spec table
- Test strategy for boundary n

## Quality gate

- [ ] O(·) stated for time and space
- [ ] At least one alternative rejected with reason
- [ ] S3c flag set or explicitly waived
- [ ] Layer placement noted
