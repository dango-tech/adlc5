# Proportionate engineering

The executable authority is `scripts/lib/policies_load.py`: `PROFILE_SKIPS`,
`step_enabled`, `next_step_for_profile`, and `profile_risk_errors`. Skills,
personas and host adapters defer to this table rather than inventing routes.

| Profile | Planning | Delivery |
|---|---|---|
| tiny | Compact `change.md`; no design or story tree | Build, verify, PR |
| standard | One `design/plan.md` at design discovery; stories and code specs | Build, verify, integrate, PR |
| high_risk | Full engineering/design ladder and independent critique | Full delivery, security checks, human PR approval |
| full (legacy) | Full ladder | Full delivery; declared risk still requires high_risk |

Auth, money, secrets, migration, concurrency, destructive changes, public
compatibility, disputed requirements or unknown risk require high_risk. A changed
trust boundary requires a new risk assessment and current readiness review.
Resolving uncertainty does not silently downgrade known risk or remove approval.

Before adding research, a pattern, an algorithm, abstraction or architecture
layer, name the design question and why existing repository structures or
standard capabilities cannot answer it. Do not run every auxiliary skill by
default. Preserve mandatory reviews on high-risk routes.

Assess operational obligations during planning, including for standard routes
that skip the full operations document. Tiny work records compact reasons in
its readiness delivery record. Relevant triggers are:

| Trigger | Consider and verify |
|---|---|
| Auth, tenants, sensitive data | Isolation, denied paths, redaction, audit behavior |
| Migration | Existing records, compatibility, rehearsal, recovery or forward-fix |
| Public API/format | Versioning, consumers, failure contracts, contract tests |
| Jobs/retries/concurrent writes | Idempotency, race/failure tests, bounded retries |
| Scale/latency target | Representative load and data, measurable resource envelope |
| Network dependency | Timeout, unavailable service, safe degradation |
| Deployment behavior | Configuration, health signals, rollout and recovery |
| UI change | Accessibility, loading/empty/error states, critical journey |

Use the [readiness delivery contract](../../docs/requirements-readiness.md).
Unknown applicability stays unresolved. Explain non-applicability; do not use a
profile to waive an applicable obligation. Preserve necessary authorization,
compatibility and failure constraints in coder context. Independent review hides
the coder's reasoning from the verifier, not requirements from the coder.

Report local checks, CI, PR readiness, deployment approval and production
observation separately. `pr-ready` establishes readiness for review; it does not
establish deployment or live production qualification.
