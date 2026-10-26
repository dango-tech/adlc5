# Definition of Done — [feature-name]

Per-feature checklist for **production-ready** delivery (not the same as story `verified`).

Copy to `.adlc5/{feature}/definition-of-done.md` on feature start, or use the copy from `.adlc5/governance/definition-of-done.md` after `init-workspace.sh`.

**Normative reference:** [production-ready.md](https://github.com/dango-tech/adlc5/blob/main/core/governance/production-ready.md) or `.adlc5/governance/production-ready.md` in a consumer workspace.

---

## Criteria (all required unless waived with user approval in lifecycle `clarity.history`)

| # | Criterion | Evidence | Gate / script |
|---|-----------|----------|---------------|
| 1 | **PR-ready gate passes** | `check-gates.py --gate pr-ready` → `status: pass` | `./scripts/check-gates.py --feature {feature} --gate pr-ready` |
| 2 | **Implement stage completed** | `stage_status.implement: completed` in `.adlc5/{feature}/state.json` | Lifecycle state |
| 3 | **Verification report in sync** | `.adlc5/{feature}/verify/verification-report.md` matches canonical `tasks.stories[]` statuses | `./scripts/sync-verification-report.sh --feature {feature}` |
| 4 | **QA deployment clearance CLEARED** | Required when the selected profile enables `implement-4-qa`; `.qa/{feature}/deployment-clearance.md` contains `CLEARED` | `check-gates.py` pr-ready |
| 5 | **PR ready** | Branch pushed; `implement.pr.status: completed` with URL | `@pr-reviewer` / `implement.pr` in state |
| 6 | **No unapproved waivers** | No `pass-with-warnings` without `clarity.history` approval; no silent `waived` craftsmanship gates | [verifier rules](https://github.com/dango-tech/adlc5/blob/main/core/governance/verifier-rules.md) |
| 7 | **Custom gates (if configured)** | All entries in `policies.yaml` `required_gates` / `custom_gates` pass | `check-gates.py` pr-ready |
| 8 | **Human PR approval (if configured)** | `clarity.history` entry `type: pr_approval`, `approved_by: user` when `autopilot.require_human_pr_approval: true` | `check-gates.py` pr-ready |

---

## Waivers

Record each waiver in `.adlc5/{feature}/state.json` → `clarity.history[]`:

```json
{
  "ts": "ISO8601",
  "type": "dod_waiver",
  "criterion": 6,
  "reason": "user-approved pass-with-warnings on story-2",
  "approved_by": "user"
}
```

---

## Optional policy-driven gates

When `.adlc5/{feature}/policies.yaml` defines `custom_gates`, criterion 7 is **mandatory** for production-ready (fail, not warn).

Example:

```yaml
custom_gates:
  - name: e2e_docker
    command: pnpm test:e2e:frontend
    cwd: frontend
required_gates:
  - e2e_docker
```

---

## Sign-off

| Role | Date | Notes |
|------|------|-------|
| Feature owner | | |
| Reviewer | | |
