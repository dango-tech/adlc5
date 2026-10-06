# Plan — Engineering + design phases

## Engineering substeps

### plan-1-engineering-architecture

Invoke `@clean-architecture-review`. Set `craftsmanship.architecture_review: completed`.

### plan-2-engineering-patterns

Invoke `@design-pattern-advisor` and `@pbe-select-patterns`. Set `craftsmanship.pattern_selection: completed`.

### plan-3-engineering-algorithms

If `scale_nfrs.applicable`, invoke `@algorithm-advisor`. Optional `@autoresearch` for evidence.

Set `craftsmanship.algorithm_review: completed` or `not_applicable`.

## Design substeps

### plan-4-design-discovery

Write `design/1a-discovery.md` — bounded context, layers, scaffold profile (greenfield → scaffold-manifest).

### plan-5-design-contracts

Write `design/1b-contracts.md` — APIs, events, integration boundaries.

### plan-6-design-operations

Write `design/1c-operations.md` — security, performance, observability, deployment.

Required sections:

1. **Threat model** — for each trust boundary and external input from `design/1b-contracts.md`, walk STRIDE (spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege). Record: threat → affected asset → mitigation (design decision, not "scan later") → residual risk. Cover the authn/authz model, data classification, and secrets handling captured in spec-handoff **NFRs & compliance**. Mitigations become code-spec tasks in `tasks-2-code-spec`; `@qa` Phase 1 verifies them, it does not replace them.
2. **Performance** — budgets against `state.scale_nfrs`; hot paths flagged for `@complexity-review`.
3. **Observability** — logs/metrics/traces per the operability NFRs; alert conditions with thresholds.
4. **Deployment & rollback** — rollout strategy, feature flags, migration/backfill ordering, rollback plan for each irreversible step.

### plan-7-design-critique

For high-risk/full work, spawn `@adlc5-design-critic` with the spec handoff,
design artifacts, explicit risk assessment, and scale NFRs. The critic records
`critique_severity: none | minor | blocking`. Clarity score alone never waives
independent critique. Rework blocking findings before advancing.

For standard work, use the compact `design/plan.md` route in the Plan skill;
these detailed substeps are conditional.

## Exit

Run `plan-complete` gate and compact stage memory.
