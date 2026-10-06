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

Check first whether a full critic pass is even warranted:

```text
clarity_score = state.clarity.score (from the latest Specify/Plan clarity check)
low_risk = not state.scale_nfrs.applicable  # false/absent counts as low_risk

if clarity_score >= 90 and low_risk:
    skip the @adlc5-design-critic spawn
else:
    spawn @adlc5-design-critic (unchanged path below)
```

**Skip path** (clear spec, no scale NFRs): write `design/design-critique.md` yourself —
no subagent, no reasoning-tier round-trip:

```markdown
# Design critique — self-check (subagent skipped)

Skipped `@adlc5-design-critic`: clarity.score = {score} (>= 90) and no scale NFRs
apply. Spec and design docs are unambiguous enough that a full critique pass
would not surface new findings proportional to its cost.

critique_severity: none
```

**Full path** (otherwise): spawn `@adlc5-design-critic` with `spec-handoff.md`,
`design/1a-discovery.md`, `design/1b-contracts.md`, `design/1c-operations.md`, and
`state.scale_nfrs` (code specs don't exist yet — Plan-scope critique). Critic
writes `design/design-critique.md` ending in a `critique_severity` verdict.

On `blocking`: route back to the cited substep (`plan-4`…`plan-6` or Specify handoff), fix, re-run the critic. Do not advance to Tasks.

If you skipped the critic and a later stage (Tasks/Implement/QA) surfaces a
design-level defect the critique would likely have caught, that's a signal the
90/no-NFR bar was too permissive for that feature — flag it, don't silently
raise the bar yourself.

## Exit

Run `plan-complete` gate and compact stage memory.
