# Assure gates — Implement stage craftsmanship checklist

Use during **Stage 4 — Implement** (substeps `implement-2-verify` … `implement-5-pr`) before marking the feature lifecycle-complete. Record completion in `.adlc5/{feature}/state.json` → `stage_status.implement: "completed"` **only** when [templates/definition-of-done.md](../../templates/definition-of-done.md) and `check-gates.py --gate pr-ready` pass.

**Normative:** [governance/production-ready.md](../governance/production-ready.md)

## Prerequisites

- [ ] Build complete: `implement-1-build` gate **pass** (all component stories `implementation_complete` or beyond)
- [ ] Code spec and tests existed before implementation (Tasks gate `tasks-2-code-spec-complete`)

## Ordered Implement completion ladder

| Step | ID | Invoke | Gate script |
|------|-----|--------|-------------|
| 1 | `implement-2-verify` | `@assure-verifier` via `@adlc5-implement` | `check-gates.py --gate implement-2-verify` |
| 2 | `implement-3-integrate` | `@adlc5-implement` | `check-gates.py --gate implement-3-integrate` (when E2E required) |
| 3 | `implement-4-qa` | `@qa` | `check-gates.py --gate implement-4-qa` |
| 4 | `implement-5-pr` | `@pr-reviewer` | `check-gates.py --gate implement-5-pr` |

QA clearance is required when the selected profile enables `implement-4-qa`; profiles that explicitly skip it continue through their remaining enabled gates.

Legacy `assure-1…4` gate IDs normalize via [gates.yaml](../gates.yaml) `legacy_aliases`.

Before **integration** (step 2), step 1 gate must pass.

Before **`stage_status.implement: completed`**, run:

```bash
./scripts/sync-verification-report.sh --feature {feature} --workspace {consumer}
./scripts/check-gates.py --feature {feature} --workspace {consumer} --gate pr-ready
```

## Verification / integration execution

Invoke: `@adlc5-implement` — do not reimplement verifier/integration logic

- [ ] Verification complete (`implement.verification.status: completed`)
- [ ] `.adlc5/{feature}/verify/verification-report.md` present and in sync with canonical `tasks.stories[]` (`sync-verification-report.sh` exit 0)
- [ ] Integration complete when required (`implement.integration.status: completed`)

## Verification report & waivers

- [ ] No `pass-with-warnings` without `clarity.history` entry `type: verifier_waiver` ([verifier-rules.md](../governance/verifier-rules.md))
- [ ] Spec-handoff **locked** items not violated (verifier blockers)

## Custom gates

- [ ] All `policies.yaml` `required_gates` / `custom_gates` pass when configured (recorded in `check-gates.py` pr-ready `checks[]`)

## S1 — Code review (CC)

Invoke: `@craftsmanship-code-review` (S1)

- [ ] Smell heuristics (G/F/N/T) applied where relevant
- [ ] No debug noise, dead code, or scope creep vs stories
- [ ] Tests meaningful (FIRST), not trivial assertions only

## S3c — Complexity (CLRS)

Invoke: `@complexity-review` (S3c) — emphasize when scale NFRs exist

- [ ] Hot paths match documented O(·)
- [ ] No accidental quadratic loops on large **n** without justification

## S6 — Pattern-aware review (PBE)

Invoke: `@pbe-review-with-patterns` (S6)

- [ ] Named patterns from Engineering/Plan reflected in code
- [ ] Variability points and boundaries respected

## Pipeline quality

Invoke: `@qa`, `@pr-reviewer` as appropriate for the repo

- [ ] When the selected profile enables `implement-4-qa`, `@qa` → `deployment-clearance.md` **CLEARED** (BLOCKED → halt; no autopilot merge)
- [ ] `@pr-reviewer` PR review feedback resolved; merge-ready
- [ ] `policies.yaml` `assure_skills_required` addressed when file present

## Autopilot vs HITL

| Concern | Policy | Behavior |
|---------|--------|----------|
| Verification | `verify_policy: auto` | Autopilot may spawn `@assure-verifier` |
| Integration | `integrate_policy: auto` | Autopilot may run `implement-3-integrate` |
| QA BLOCKED | — | Always HITL / halt |
| PR merge | — | Always HITL |
| PR approval | `autopilot.require_human_pr_approval: true` | `pr-ready` fails without `clarity.history` `pr_approval` entry |

## Exit

- [ ] Verification + integration done (or documented skip)
- [ ] Every profile-enabled completion step and `implement-5-pr` done
- [ ] `pr-ready` gate **pass**
- [ ] Craftsmanship + pipeline gates satisfied
- [ ] `stage_status.implement: completed` — feature **production-ready** for ADLC5
