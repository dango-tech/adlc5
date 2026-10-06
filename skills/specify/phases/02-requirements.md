# Specify — Step 2: Requirements

## Invoke

`@prt for [feature]` or import existing PRD.

Artifacts: `.prt/{feature}/prt.md`

## Clarity gate

Run clarity scoring before advance — threshold from `state.clarity.threshold` (default 80).

## State

- Advance using `adlc5 transition specify-3-nfr --feature "{feature}"` after the step succeeds.
