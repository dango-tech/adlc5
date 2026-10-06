---
name: autoresearch-baseline
description: Phase 2 — Baseline & Smoke Test. Run the unmodified artifact end-to-end, capture the metric, store as trial-0000 (baseline).
---

# Phase 2 — Baseline & Smoke Test

## Purpose

Every trial in Phase 3 is judged **vs the baseline** and **vs the current best**. Without a clean baseline run there is no leaderboard, no accept/reject decision, and no fair comparison.

This phase also verifies the **execute command** and **metric extract command** from intake actually work — failing here is far cheaper than failing on trial 27.

## Entry

Pre-conditions:

- `phase_status.intake: "completed"`
- `context.target.execute_cmd`, `context.target.metric_extract_cmd`, `context.target.artifact_path` all set

## Steps

### Step 1: Snapshot the unmodified artifact

The orchestrator calls:

```bash
skills/autoresearch/scripts/run-experiment.sh \
  --project {name} \
  --trial-id baseline \
  --no-mutate
```

`--no-mutate` instructs the script to copy the artifact as-is into `experiments/baseline/` and run it.

### Step 2: Run with per-trial budget

`run-experiment.sh` runs `execute_cmd` with the per-trial budget enforced (timeout for wall-clock; step counter for step-count; dataset cursor for dataset-pass). It writes:

- `experiments/baseline/artifact.<ext>` — snapshot
- `experiments/baseline/run.log` — full stdout/stderr
- `experiments/baseline/metric.txt` — extracted scalar (via `metric_extract_cmd`)
- `experiments/baseline/exit_code` — process exit code

### Step 3: Verify metric extraction

If `metric.txt` is missing or unparseable, the smoke test **fails**. Surface the run log to the user and route back to Phase 1 Step 5 (execute command) or `metric_extract_cmd`.

Acceptable values:

- A single number (e.g. `1.234`)
- A line `metric_name: value` (the extractor normalizes)

### Step 4: Record baseline in state

The orchestrator calls:

```bash
skills/autoresearch/scripts/log-experiment.sh \
  --project {name} \
  --trial-id baseline \
  --status kept \
  --parent none \
  --mutation-summary "baseline (unmodified artifact)"
```

Effect on `state.json`:

```json
{
  "baseline": {
    "metric_value": 1.234,
    "trial_id": "baseline",
    "captured_at": "ISO8601"
  },
  "trials": {
    "baseline": { "status": "kept", "metric_value": 1.234, "mutation_summary": "baseline (unmodified)" }
  },
  "leaderboard": {
    "best_trial_id": "baseline",
    "best_metric_value": 1.234,
    "updated_at": "ISO8601"
  }
}
```

### Step 5: Initialize `leaderboard.md`

```markdown
# Leaderboard — {project}

Metric: `val_bpb` (lower is better)
Per-trial budget: 5m wall clock

| Rank | Trial | Metric | Δ vs baseline | Parent | Mutation |
|------|-------|--------|---------------|--------|----------|
| 1 | baseline | 1.234 | 0.000 | — | baseline (unmodified) |
```

The script writes this; the orchestrator does not paste it inline.

## Quality checklist

- [ ] `run-experiment.sh --no-mutate` exited 0
- [ ] `metric.txt` contains a finite number
- [ ] `state.json.baseline.metric_value` is set
- [ ] `leaderboard.md` exists with baseline row
- [ ] Run log is non-empty and readable

## Failure handling

| Failure | Action |
|---------|--------|
| Execute command exits non-zero | Show last 50 lines of log; AskQuestion: `fix_execute_cmd` (back to Phase 1.5) / `fix_artifact` / `abort` |
| Metric extract returns empty / NaN | Same as above with `fix_metric_extract` option |
| Budget exceeded on baseline | Raise per-trial budget or simplify artifact; route to Phase 1.4 |

Never proceed to Phase 3 without a clean baseline.

## Phase advance (AskQuestion)

```
Phase 2 — Baseline {metric_name}={value}. Ready for Phase 3 — Experiment Loop?
- yes — start trials
- rerun-baseline — measurement variance check (run baseline 2–3× and keep best/median)
- pause
```

Optional **variance check** (recommended for wall-clock metrics): rerun baseline 2× more, store as `baseline-v2`, `baseline-v3`, document spread in `program.md` Notes.

Set `phase_status.baseline: "completed"`, `current_phase: "autoresearch-3-loop"`.
