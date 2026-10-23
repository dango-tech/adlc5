# ADLC5 — Clarity lint and requirements readiness

Clarity is a heuristic document-lint report. `clarity.score`, threshold and history
remain readable for compatibility; the numeric value never authorizes progression.
The scorer checks surface signals and can award 100 to placeholder text.

```bash
./scripts/adlc5 clarity path/to/spec.md --step-id specify-2-requirements
```

Output retains the legacy score/breakdown and declares `heuristic: true` and
`gate_authority: false`. Use missing sections, vague language and assumption tags
as investigation hints, not a quantified measure of understanding.

## Current progression contract

Before leaving Specify, write the existing intent artifacts and `risk.json`, select
the risk-appropriate policy, then use `adlc5 readiness prepare --feature NAME`.
Review behavior, contradictions, negative cases and assumptions against current
sources. Fill actual requirement references, acceptance scenarios, decisions and
session identities, then submit `adlc5 readiness record --feature NAME --file PATH`.
See [requirements readiness](../../docs/requirements-readiness.md) for the full contract.

The kernel requires a current record at protected transitions and gates. Empty
sections, placeholders, unresolved decisions, stale sources or missing review
cannot be waived by a high score. High-risk intent requires an independent reviewer
session. Agent assumptions remain distinct from user decisions and cannot resolve
a blocking decision. Inspect available evidence before asking the user; do not
infer completeness from either the length of a prompt or the absence of tags.

## Resume and change

Preserve existing answers and approved execution scope. Changed intent, risk,
effective policies, scope or scale NFRs requires reassessment. Implementation edits
alone do not stale the intent review. Read legacy states normally, but assess an
active legacy feature before its next protected transition. Never manufacture a
review from a historical score or rewrite approval history to clear this check.
