# Plan stage — craftsmanship gates

Use during **Stage 2 — Plan** before advancing to **Tasks**. Record results in `.adlc5/{feature}/state.json` → `craftsmanship`; `stage_status.plan` is completed only after all enabled Plan steps pass or are explicitly waived.

## Prerequisites

- [ ] Specify complete: requirements, AC, scale NFRs documented
- [ ] [Playbook](../../shared/docs/playbook.md) consulted for stage and craftsmanship fit

## S2 — Architecture (CA)

Invoke: `@clean-architecture-review` (S2)

- [ ] Dependency rule: source dependencies point inward
- [ ] Layers identified (entities, use cases, adapters, frameworks)
- [ ] Large-scope-first: boundaries match the feature scope, not file-by-file drift
- [ ] `craftsmanship.architecture_review`: **pass** or **waived** (document reason)

## S3 / S5 — Patterns (HFDP + PBE)

Invoke: `@design-pattern-advisor` (S3) and/or `@pbe-select-patterns` (S5)

- [ ] GoF / OO pattern choice named with context (not default Singleton)
- [ ] Patterns fit forces; composition over inheritance where applicable
- [ ] `craftsmanship.pattern_selection`: **pass** or **waived**

## S3b — Algorithms (CLRS, when scale NFRs exist)

Invoke: `@algorithm-advisor` (S3b) — **skip** (`algorithm_review: na`) when no throughput/latency/volume concerns

- [ ] Expected **n** order documented
- [ ] Time/space **O(·)** stated for hot paths
- [ ] Data structure choice justified vs alternatives
- [ ] `craftsmanship.algorithm_review`: **pass**, **na**, or **waived**

## S4 — Pattern opportunity (PBE)

Invoke: `@pbe-pattern-opportunity` (S4)

- [ ] Rule of Three / recurrence noted if catalog candidate
- [ ] No premature org-catalog commitment without ROI (S8 later)

## Exit

- [ ] Plan decisions captured (architecture note, pattern names, O(·) if applicable)
- [ ] All required gates **pass** or **waived** with user acknowledgment
- [ ] Ready to advance to **`@adlc5-tasks`**

**Blocked:** Do not start Tasks until this checklist is satisfied or the relevant Plan steps are explicitly **waived** in `state.json`.
