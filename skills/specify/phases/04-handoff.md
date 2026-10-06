# Specify — Step 4: Handoff

Write `.adlc5/{feature}/spec-handoff.md` with:

- Problem statement
- Functional requirements + AC
- Scale NFRs (or N/A)
- NFRs & compliance (enterprise checklist from [03-nfr.md](03-nfr.md); every category answered or explicit N/A)
- Locked decisions (verifier blockers if changed)
- Out of scope

## Gate

```bash
./scripts/check-gates.py --feature "{feature}" --gate specify-complete
```

Copy [templates/feature-docs/README.md](../../../templates/feature-docs/README.md) to `.adlc5/{feature}/docs/README.md`.

## State

- `stage_status.specify`: `completed`
- Keep `current_stage: specify` and `current_step: specify-4-handoff` while
  running `./scripts/adlc5 pilot --feature "{feature}"`.
- Apply the returned `suggested_next` with `adlc5 state set`: `tiny` routes to
  `implement-1-build`, `standard` to `tasks-1-stories`, and `high_risk` to
  `plan-1-engineering-architecture`. Set `current_stage` from that step prefix
  and mark the selected stage `in_progress`; mark any skipped `plan`/`tasks`
  stages `waived` so state records the deliberate profile route.

Compact memory:

```bash
./scripts/memory/compact-stage.sh --feature "{feature}" --stage specify
```
