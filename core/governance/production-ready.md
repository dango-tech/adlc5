# Production-ready (normative)

**Story verified ≠ production-ready.**

A feature may have every component story `verified` in canonical `.adlc5/{feature}/state.json` while still failing enterprise delivery gates.

## Definitions

| Term | Meaning |
|------|---------|
| **Story verified** | Canonical `tasks.stories[].status == verified` after `@assure-verifier` |
| **Implement complete** | Canonical `stage_status.implement == completed` with required verification, integration, QA, and PR evidence recorded under `implement` |
| **Production-ready** | All criteria in [definition-of-done.md](https://github.com/dango85/adlc5/blob/main/templates/definition-of-done.md) satisfied |
| **PR-ready** | Deterministic gate `pr-ready` passes via `check-gates.py` |

## Implement ladder (lifecycle)

Canonical step IDs: [core/sdd-model.md](https://github.com/dango85/adlc5/blob/main/core/sdd-model.md). Legacy `assure-*` IDs normalize via [gates.yaml](https://github.com/dango85/adlc5/blob/main/core/gates.yaml) `legacy_aliases`.

| Step ID | Display label | Primary invoke |
|---------|---------------|----------------|
| `implement-2-verify` | Verification | `@assure-verifier` (spawned by `@adlc5-implement`) |
| `implement-3-integrate` | Integration & E2E | `@adlc5-implement` |
| `implement-4-qa` | Quality & security | `@qa` |
| `implement-5-pr` | PR review & open | `@pr-reviewer` |

Lifecycle `stage_status.implement: completed` requires **PR-ready gate pass** and the [Implement completion gates](https://github.com/dango85/adlc5/blob/main/core/checklists/assure-gates.md) — not verification alone.

## Deterministic gate

From consumer workspace root:

```bash
{adlc5_root}/scripts/check-gates.py --feature {feature} --workspace {consumer} --gate pr-ready
```

Exit `0` + JSON `status: pass` → PR-ready. Exit `1` → blocked; orchestrator lists `checks[]` gaps.

## Human approval (optional policy)

When `policies.yaml` sets `autopilot.require_human_pr_approval: true`, `pr-ready` additionally requires a `clarity.history` entry of `type: pr_approval` with `approved_by: user` in `.adlc5/{feature}/state.json`. Use this in autonomous mode so no PR is declared production-ready without a human sign-off. See the [policy template](https://github.com/dango85/adlc5/blob/main/templates/policies.yaml.example).

## Orchestrator status check

`@adlc5` compares Implement completion vs production-ready on every invocation — see the [ADLC5 skill](https://github.com/dango85/adlc5/blob/main/skills/adlc5/SKILL.md).

## Autopilot endpoint

When the selected profile enables `implement-4-qa`, `pr-ready` requires QA clearance; profiles that explicitly skip that step do not fabricate a QA obligation. Every profile still requires its enabled steps and `implement-5-pr`. See [autopilot-stage-picker.md](https://github.com/dango85/adlc5/blob/main/core/governance/autopilot-stage-picker.md).

## Beyond PR

ADLC5's autopilot delivers **spec → PR**. Past the PR, two optional HITL skills orchestrate the consumer's pipeline (which executes all provisioning):

| Skill | Role | Gate |
|-------|------|------|
| [`@infra`](https://github.com/dango85/adlc5/blob/main/skills/infra/SKILL.md) | IaC authoring/validation post-Plan; baseline report for `@qa` | validation clean, no unresolved criticals |
| [`@deploy`](https://github.com/dango85/adlc5/blob/main/skills/deploy/SKILL.md) | Runbook + pipeline trigger + post-deploy verification | `check-gates.py --gate deploy-ready` |

`deploy-ready` requires QA clearance `CLEARED`, the PR recorded, and a `clarity.history` entry `{type: deploy_approval, approved_by: user}` — **in every mode**, so `autopilot.endpoint: merged | deployed` can extend the autopilot only up to that human sign-off, never through it. The QA step's `deployment-clearance.md` is the handoff contract; the [security workflow template](https://github.com/dango85/adlc5/blob/main/templates/github-workflows/security-scan.yml) is a starter CI hook consumers extend with deploy jobs.
