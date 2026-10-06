---
name: deploy
description: Deploy — clearance-gated deployment orchestration after pr-ready/merge. Verifies deployment-clearance.md, human approval, and rollback plan via the deploy-ready gate, produces a deployment runbook, drives the consumer's pipeline (never provisions directly), and runs post-deploy verification. Always HITL for production.
author: ADLC5 Contributors
---

# Deploy — clearance-gated deployment orchestration

## Intent

Take a merged, QA-cleared feature through deployment **via the consumer's pipeline**. This skill gates, plans, triggers, and verifies — it does not run provisioning commands itself. Production promotion is **always human-confirmed**; there is no autonomous path to prod.

**Invoke:** `@deploy for [feature]`

**Pipeline position:**

```
pr-ready → merge → @deploy (deploy-ready gate → runbook → pipeline trigger → verify)
```

## Model recommendation

**Tier:** reasoning (irreversible-action planning). Map tier → host model via `config.yaml` `model_profiles`.

## Hard gate (before anything else)

```bash
./scripts/adlc5 gate --feature "{feature}" --gate deploy-ready
```

| Check | Requirement |
|-------|-------------|
| `qa_clearance` | `.qa/{feature}/deployment-clearance.md` is `CLEARED` (or `CLEARED-WITH-EXCEPTIONS` with acknowledged risks) |
| `pr_recorded` | PR URL in lifecycle state (`implement.pr.url` / `pr_review.url`); warn if merge not recorded |
| `deploy_approval` | `clarity.history` entry `{type: deploy_approval, approved_by: user}` — **always required, in every mode** |

Gate fails → stop and report the gaps. Never work around a `BLOCKED` clearance.

## Step ladder

| Step | Purpose | Artifact |
|------|---------|----------|
| `deploy-0-gates` | Run `deploy-ready`; AskQuestion for `deploy_approval` + target environment | state |
| `deploy-1-plan` | Runbook from `1c-operations.md` deployment/rollback design | `.deploy/{feature}/deployment-plan.md` |
| `deploy-2-execute` | Trigger the consumer pipeline; watch it | pipeline run link in state |
| `deploy-3-verify` | Post-deploy verification; rollback decision | `.deploy/{feature}/post-deploy-verification.md` |

State: `.deploy/{feature}/state.json` (stage-local).

### deploy-0-gates

Run the gate. If `deploy_approval` is missing, AskQuestion for sign-off naming the exact target environment and submit it with `adlc5 evidence approve --file approval.json` using `type: deploy_approval`, the actual human provenance label, and target `environment` — never write this entry without an explicit user response. Approval is **per environment**: promoting staging → prod requires a new entry.

### deploy-1-plan

Write `deployment-plan.md` from `design/1c-operations.md`: ordered steps (migrations/backfills first, per their documented ordering), feature-flag states, environment promotion path, **rollback procedure for every irreversible step**, verification checks with thresholds, and abort criteria. A plan without a rollback section is incomplete — route back to Plan if `1c` lacks one.

### deploy-2-execute

Drive the consumer's own pipeline — trigger the CI workflow (e.g. `gh workflow run`, pipeline API) or hand the operator the exact commands from the runbook. [github-workflows/security-scan.yml](../../templates/github-workflows/security-scan.yml) is the starter CI shape consumers extend with deploy jobs. Record the pipeline run URL in state. **Do not** run `terraform apply` / `kubectl apply` / cloud CLIs yourself.

### deploy-3-verify

Execute the verification checks from the runbook (health endpoints, error rates vs the observability thresholds in `1c`, smoke flows). Write `post-deploy-verification.md` with each check's result. Any abort criterion met → recommend rollback per the runbook and AskQuestion immediately; do not wait out a degrading deploy.

## Never do

- ❌ Proceed on `BLOCKED` clearance or a failed `deploy-ready` gate
- ❌ Deploy to production without a fresh `deploy_approval` for that environment
- ❌ Run provisioning/rollout commands directly — the consumer pipeline executes; you orchestrate
- ❌ Write a `deploy_approval` entry the user didn't explicitly give
- ❌ Skip the rollback section or post-deploy verification

## Autopilot boundary

`policies.yaml` `autopilot.endpoint: merged | deployed` extends the autopilot past `pr_ready` only as far as **invoking this skill's gate** — the `deploy_approval` check makes an unattended production deploy impossible by construction. See [production-ready.md](../../core/governance/production-ready.md).
