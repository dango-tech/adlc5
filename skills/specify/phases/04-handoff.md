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

## Progression

Record `risk.json` and the selected profile before implementation. Tiny work uses
`change.md` for its bounded reuse/scope/acceptance/risk decisions; standard work
continues into brief Plan. Run `adlc5 pilot` and apply its `suggested_next` with
`adlc5 transition TARGET --feature "{feature}"`. The kernel validates gates and
updates progression; never patch stage/step/completion fields with `state set`.

Compact memory:

```bash
./scripts/memory/compact-stage.sh --feature "{feature}" --stage specify
```
