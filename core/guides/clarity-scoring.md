# ADLC5 — Clarity scoring

Quantify requirement/design readiness before stage and step advances. Works with [interaction-modes.md](interaction-modes.md) and the canonical [SDD model](../sdd-model.md).

## State schema

Add to `.adlc5/{feature}/state.json`:

```json
"clarity": {
  "threshold": 80,
  "score": 65,
  "history": [
    {
      "ts": "2026-05-20T12:00:00Z",
      "type": "clarity_check",
      "step": "specify-2-requirements",
      "score": 65,
      "open_items": 2,
      "assumptions": 1
    }
  ]
}
```

Initialize on first `@adlc5` invocation with `threshold: 80`, `score: null`, and empty `history`.

## Scoring rubric (0–100 per step)

| Dimension | Weight | Signals |
|-----------|--------|---------|
| **Completeness** | 30% | Required sections filled; AC present; scale NFRs captured or explicitly N/A |
| **Specificity** | 30% | Measurable AC; named entities; no vague terms ("fast", "user-friendly") without targets |
| **Confirmed vs assumed** | 25% | User-confirmed decisions vs `[ASSUMPTION]` flags in artifacts |
| **Testability** | 15% | QA could write tests without guessing behavior |

Record `open_items` = count of unresolved ambiguities; `assumptions` = count of `[ASSUMPTION]` tags.

## When to score

To perform repeatable quantitative scoring of a document or spec, call the automated clarity scoring script:

```bash
./scripts/clarity-score.py /path/to/spec.md --step-id "{step-id}"
```

This script scans for `[ASSUMPTION]` tags, checks completeness criteria, detects unquantified vague terms (like "fast", "scalable"), analyzes testability markers, and outputs a structured JSON report ready to be merged into `state.json`.

| Pipeline | Score before advance |
|----------|---------------------|
| Specify (`specify-*`) | Always (HITL mode) |
| Plan (`plan-*`) | Always (HITL mode) |
| Tasks / Implement | Re-score when unresolved assumptions affect the active step |

## HITL clarification loop (Specify + Plan)

When interaction mode is `hitl` (default) and `clarity.score < clarity.threshold`:

1. Score artifact → write `clarity.score` and append a `clarity.history` entry for the step
2. List top 3 ambiguities (rank by implementation risk)
3. **AskQuestion** — max 2 questions per call; repeat until resolved or waived
4. Update artifact; remove resolved `[ASSUMPTION]` tags
5. Re-score
6. Stage/step-advance **AskQuestion** only after score ≥ threshold OR user selects **Proceed with documented assumptions**

### Discover pre-check (Specify stage)

Before skipping `@discover`:

| Input clarity (informal) | Action |
|--------------------------|--------|
| Score < 60 | **Require** `@discover` or clarification round before `@prt` |
| 60–79 | Offer `@discover`; run clarification if user declines discover |
| ≥ 80 + user confirms | Skip discover; proceed to `@prt` |

Do not infer "requirements already clear" from a short prompt alone.

## Waive

Use AskQuestion option id `proceed_with_assumptions` — document waived step and remaining assumptions in `clarity.history` with `action: "waived"`.

## Overall score

`clarity.score` records the current blocking readiness score. Use the minimum active Specify/Plan score for gate decisions so one weak step blocks downstream work.

## Tasks / Implement escalation

- [@build-implementer](../../skills/build-implementer/SKILL.md): if code-spec step score was below threshold at waive, escalate ambiguity — do not guess
- [@adlc5-tdd](../../skills/adlc5-tdd/SKILL.md): spec ambiguous → report; don't guess
