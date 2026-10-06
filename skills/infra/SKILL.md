---
name: infra
description: Infra — IaC authoring and validation for a feature. Maps design/1c-operations.md to infrastructure code, validates and security-scans it (never applies), and produces .infra/{feature}/infra-validation-report.md, the baseline @qa de-duplicates against. Optional post-Plan step before @qa.
author: ADLC5 Contributors
---

# Infra — IaC authoring & validation

## Intent

Turn the deployment/operations design into validated infrastructure-as-code. **Validation only** — this skill never provisions. Runs after Plan (needs `design/1c-operations.md`), typically alongside Implement and before `@qa`.

**Invoke:** `@infra for [feature]`

**Pipeline position:**

```
Plan (1c-operations) → @infra → infra/ + .infra/{feature}/infra-validation-report.md → @qa (baseline) → @deploy
```

## Model recommendation

**Tier:** reasoning (security-sensitive design mapping). Map tier → host model via `config.yaml` `model_profiles`.

## Step ladder

| Step | Purpose | Artifact |
|------|---------|----------|
| `infra-0-discovery` | Detect IaC tooling and cloud target | `state.context` |
| `infra-1-mapping` | Map `1c-operations.md` + NFRs to infra components | `.infra/{feature}/infra-plan.md` |
| `infra-2-author-validate` | Author `infra/` code; run fmt/validate/plan | `infra/` |
| `infra-3-scan-baseline` | IaC security scan; write baseline report | `.infra/{feature}/infra-validation-report.md` |

State: `.infra/{feature}/state.json` (stage-local; lifecycle `.adlc5/{feature}/state.json` stays authoritative).

### infra-0-discovery

Detect existing `infra/` code, IaC toolchain (Terraform, Pulumi, CloudFormation, Kubernetes manifests, Docker Compose), and cloud target from the repo and `design/1c-operations.md`. If none is prescribed, AskQuestion: toolchain and target environment(s). Record in `state.context`.

### infra-1-mapping

Read `design/1c-operations.md` (deployment & rollback, observability, threat model) and spec-handoff **NFRs & compliance**. Write `.infra/{feature}/infra-plan.md`: components (compute, network, data, secrets manager, observability), environment matrix (dev/staging/prod), and which NFR each component satisfies. Flag anything in `1c` with no infra answer as a gap — do not silently drop requirements.

### infra-2-author-validate

Author or update `infra/` following the platform supplements:

- [TERRAFORM-CODING-GUIDELINES.md](../../core/guides/platform-supplements/TERRAFORM-CODING-GUIDELINES.md)
- [TERRAFORM-AWS-SUPPLEMENT.md](../../core/guides/platform-supplements/TERRAFORM-AWS-SUPPLEMENT.md) / [TERRAFORM-GCP-SUPPLEMENT.md](../../core/guides/platform-supplements/TERRAFORM-GCP-SUPPLEMENT.md)

Validate without provisioning: `terraform fmt -check && terraform validate` (and `terraform plan` only when the user confirms credentials/backends are safe to read), `kubectl apply --dry-run=client`, `docker compose config`, or the toolchain equivalent.

### infra-3-scan-baseline

Run the available IaC scanner (`checkov`, `tfsec`, `trivy config`) over `infra/`. Write `.infra/{feature}/infra-validation-report.md`: every finding with rule ID, resource, file:line, severity, and fix/acceptance status. This is the **baseline `@qa` Phase 1 de-duplicates against** — findings you accept here must carry a rationale, since `@qa` will not re-flag them.

## Gate

Before handing to `@qa`: validation clean (or failures listed as blockers), no unresolved **critical** scanner findings, report written. Record `infra: completed` in `.infra/{feature}/state.json`.

## Never do

- ❌ `terraform apply`, `kubectl apply` (non-dry-run), or any provisioning command
- ❌ Write cloud credentials, state backends with secrets, or `.tfvars` secrets into the repo
- ❌ Accept a critical finding without explicit user acknowledgment recorded in the report
- ❌ Invent infra for requirements absent from `1c-operations.md` — route gaps back to Plan

## Autonomous mode

Under `@adlc5` autopilot (`autopilot.interaction_mode: autonomous`): skip preference questions when `1c-operations.md` prescribes the toolchain; auto-advance steps; **halt** (hard escalation `security_critical`) on critical scanner findings or missing toolchain decision. Provisioning remains impossible in any mode.
