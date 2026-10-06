# Specify — Step 3: NFRs & enterprise constraints

Two capture targets: **scale NFRs** in state (drives `plan-3-engineering-algorithms`), and the **enterprise NFR checklist** in `spec-handoff.md` (drives Plan design steps and `@qa` targets).

## Scale NFRs (state)

Capture throughput, latency, volume in `state.scale_nfrs`.

If not applicable, record `"applicable": false` and set `craftsmanship.algorithm_review` to `not_applicable`.

## Enterprise NFR checklist (spec-handoff)

Walk each category with the user (AskQuestion, batch related items). Record every answer — including explicit "N/A" — in the **NFRs & compliance** section of `spec-handoff.md`. Unaddressed categories block `specify-complete` review in HITL mode; in autonomous mode record `default: N/A` with rationale.

| Category | Capture |
|----------|---------|
| **Availability & resilience** | SLO/uptime target, RTO/RPO, degradation behavior, retry/idempotency expectations |
| **Security** | AuthN/AuthZ model, data classification (PII/PHI/PCI), encryption at rest/in transit, secrets handling, audit logging |
| **Compliance** | Applicable regimes (GDPR, HIPAA, SOC 2, PCI DSS, data residency) — feeds `@qa` Phase 4 policy enforcement |
| **Data** | Retention/deletion policy, migration/backfill needs, backwards compatibility of schemas and APIs, versioning/deprecation policy |
| **Operability** | Observability expectations (logs/metrics/traces), alerting thresholds, feature flags, rollout/rollback strategy |
| **UX quality** | Accessibility target (e.g. WCAG 2.1 AA), i18n/l10n, supported platforms/browsers |

Downstream consumers:

- `plan-6-design-operations` → threat model + operations design in `design/1c-operations.md`
- `@qa` Phase 3/4 → performance targets, accessibility target, compliance regimes
- `tasks-2-code-spec` → NFR-derived test cases (e.g. authz denial paths, retention jobs)

## State

- Advance using `adlc5 transition specify-4-handoff --feature "{feature}"` after the step succeeds.
