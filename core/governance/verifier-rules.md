# Verification rules (normative)

Applies to `@assure-verifier` at `implement-2-verify`. Consumer copy: `.adlc5/governance/verifier-rules.md`.

## Report artifact (required)

Every verification batch must create or update:

`.adlc5/{feature}/verify/verification-report.md`

Aggregate section **Overall** must match triage: `pass` | `pass-with-warnings` | `fail`.

Orchestrator runs:

```bash
./scripts/sync-verification-report.sh --feature {feature} --workspace {consumer}
```

before marking `implement.verification.status` **completed**.

## Overall pass

- **pass** — no blockers; warnings allowed only if user approved (see below)
- **fail** — one or more blockers
- **pass-with-warnings** — no blockers but warnings present → **requires user approval** before story → `verified`

## pass-with-warnings

Forbidden as silent success. Orchestrator must:

1. **AskQuestion** — proceed with warnings vs rework (unless lifecycle already has approval)
2. Record approval in `.adlc5/{feature}/state.json`:

```json
"clarity": {
  "history": [
    {
      "ts": "ISO8601",
      "type": "verifier_waiver",
      "story_id": "story-2",
      "overall": "pass-with-warnings",
      "approved_by": "user"
    }
  ]
}
```

Without a matching `verifier_waiver` entry, `check-gates.py` and `sync-verification-report.sh` treat warnings as **blocking** for verification completion.

## Spec-handoff locked decisions

Items marked **locked** in `.adlc5/{feature}/spec-handoff.md` (or PRT AC marked immutable) are **blockers** if implementation contradicts them — even when code spec is internally consistent.

Flag in verifier report: `escalated: spec_handoff_violation`.

## Sync with canonical state

Per-story status in the report must match canonical `state.json` `tasks.stories[].status` and `implement.verification` evidence.

Older state layouts remain a script-level compatibility concern; current verification guidance writes only canonical schema-v3 state.

## Hard escalation (autonomous mode)

- `unapproved_verifier_waiver` — warnings without `clarity.history` approval
- `verification_report_out_of_sync` — `sync-verification-report.sh` exit non-zero

See the [ADLC5 skill](https://github.com/dango-tech/adlc5/blob/main/skills/adlc5/SKILL.md) (autonomous mode) and `scripts/pilot-autopilot.sh`.
