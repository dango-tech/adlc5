---
title: ADLC5 Pulse
description: Read an on-demand local view of ADLC5 feature progress, evidence and usage.
---

# ADLC5 Pulse

Pulse is an on-demand snapshot of ADLC5 feature progress, recorded evidence, usage coverage, and a suggested next action. It uses the existing ADLC5 state and evidence and does not run consumer commands, change lifecycle state, or continuously monitor a repository.

```bash
./scripts/adlc5 pulse snapshot --workspace .
./scripts/adlc5 pulse band --workspace . --feature my-feature
./scripts/adlc5 pulse board --workspace . --open
./scripts/adlc5 pulse handoff --workspace . --feature my-feature
```

`snapshot` and `band` are read-only. `board` explicitly writes a local, self-contained offline page and a derived cache under the consumer's ignored `.agent-cache/pulse/`. Rerun `board` to refresh it. `handoff` prints a summary for review; it does not write to a clipboard or send it elsewhere.

Evidence is current at capture time. A local `pr-ready` gate observation is not remote CI, human approval, deployment, or production health. `known_cost_usd` is an attributable subtotal, not an invoice; `complete_total_usd` stays null because ledger coverage is unproven. Missing, unavailable, or unpriced records remain unknown. See the [full Pulse guide](https://github.com/dango-tech/adlc5/blob/main/docs/pulse.md) for security, data, and plugin details.

The same skill and read-only snapshot tool ship in the Codex, Claude Code, and Cursor packages. Claude Code also displays a native interactive band above the prompt, refreshed at session start and after completed turns. Review and Audit invoke existing skills; Board writes and opens the offline board; Details expands the captured evidence. Codex and Cursor use the shared skill/MCP/CLI interfaces because their documented plugin surfaces do not expose a persistent custom prompt band. Claude may still use an optional cached status line configured manually. Live host qualification remains separate from package tests.

## Savings and quality

The card and board show outcome success with sample counts, projected cost savings from observed comparable runs, escaped defects, and rework. Missing evidence displays **Not measured**. Outcome success is not a general accuracy score. The board shows a 95% Wilson interval for the recorded success proportion and an observed case range for savings; neither proves future performance.

Place actual evaluator exports (`telemetry.jsonl`, `usage.jsonl`, `outcomes.jsonl`) under `.adlc5/<feature>/evaluation/`. Savings require explicitly matched direct/candidate cases, equal repetitions, complete reported costs, and every run passing the existing quality floor. The experiment owner declares comparability with `comparison_id`; Pulse does not verify experimental design. No evaluation data is uploaded. See the [full Pulse guide](https://github.com/dango-tech/adlc5/blob/main/docs/pulse.md#savings-and-quality-on-the-card-and-board) for the record contract.
