---
name: autoresearch-loop
description: Phase 3 — Experiment Loop. Propose mutation → run → measure → accept/reject → log. Repeats until budget exhausted, kill-switch tripped, or user stops.
---

# Phase 3 — Experiment Loop

## Purpose

The core loop. Each trial:

1. **Propose** a single mutation to the artifact
2. **Run** the mutated artifact under the per-trial budget
3. **Measure** the metric
4. **Decide** keep (new leaderboard entry) or discard
5. **Log** the trial regardless of decision

This is the karpathy invariant — keep the loop tight and the decisions cheap. See [guides/knowledge-base.md](../guides/knowledge-base.md) for the source mapping.

## Entry

Pre-conditions:

- `phase_status.baseline: "completed"`
- `state.json.baseline.metric_value` is finite
- `program.md` exists and is current

## Mode selection

Read `context.interaction_mode`.

| Mode | Behavior |
|------|----------|
| `hitl` | Orchestrator proposes one mutation, runs **one trial**, presents result, AskQuestion (keep/discard/refine/stop). User drives loop. |
| `autonomous` | Orchestrator spawns `@autoresearch-experimenter` subagents up to `max_trials`, checking the kill-switch and budget between trials. No per-trial confirmation. |

Both modes use identical scripts; only the confirmation point differs.

## The loop (per trial)

### Step 1: Pre-trial gate

Before every trial, the orchestrator runs:

```bash
skills/autoresearch/scripts/check-kill-switch.sh --project {name}
```

Exits non-zero if:

- `STOP` file present at `context.safety.kill_switch_path`
- `max_trials` reached
- `max_total_wall_clock` exceeded
- `cost_cap_usd` exceeded (when set)
- N consecutive failed trials (tripwire — default N=3)

On non-zero exit, **stop the loop** and run **AskQuestion** (required when `definition_of_done.confirm_each_exit` is true — campaign default):

| `id` | Meaning |
|------|---------|
| `dod_budget_exhausted` | Budget exhausted — end loop (default) |
| `dod_metric_plateau` | No meaningful improvement — end loop |
| `dod_target_met` | Target metric reached — end loop |
| `dod_continue` | Extend budget and continue |

Record choice in `tasks/{task_id}/definition-of-done.md` and task `state.json`, then route to Phase 4.

### Step 2: Propose mutation

Read [guides/mutation-strategies.md](../guides/mutation-strategies.md) and `program.md`. The orchestrator (or experimenter subagent) chooses **one** mutation. Examples:

| Target shape | Example mutation |
|--------------|------------------|
| `ml-training` | Change `DEPTH` from 8 to 12; or swap optimizer Muon → AdamW; or alter `WINDOW_PATTERN` |
| `prompt-tuning` | Reorder reasoning steps; add a worked example; tighten constraint wording |
| `retrieval-tuning` | Swap encoder; change `top_k`; add reranker |
| `algorithm-perf` | Replace `dict` lookup with array; precompute prefix sums; vectorize hot loop |
| `hyperparam-search` | Adjust one numeric hyperparameter |

**Single-mutation rule:** One change per trial. Two changes → unattributable result.

Write a one-line `mutation_summary` (≤ 120 chars) before running. This is the leaderboard's "why".

### Step 3: Run

```bash
skills/autoresearch/scripts/run-experiment.sh \
  --project {name} \
  --trial-id trial-{NNNN} \
  --parent {best_trial_id_or_baseline} \
  --mutation-summary "<one line>"
```

The script:

1. Copies the parent's snapshot into `experiments/trial-NNNN/`
2. Applies the mutation in-place (the orchestrator or experimenter must have already produced the new artifact and passed `--mutated-artifact <path>`, or the experimenter writes directly into the trial dir)
3. Runs `execute_cmd` with the per-trial budget
4. Writes `metric.txt`, `run.log`, `exit_code`, `diff.patch` (vs parent)

### Step 4: Measure + decide

The script returns the metric (or `failed` on non-zero exit / unparseable metric).

| Outcome | Decision rule |
|---------|---------------|
| Metric improves vs **current best** by ≥ `min_improvement` (default 0) | `kept` |
| Metric is within noise band of current best | `discarded` (default), unless `tie_policy: keep_newer` |
| Metric regresses | `discarded` |
| Trial failed | `failed`, increment tripwire counter |

In `hitl` mode, the orchestrator presents the result and AskQuestion:

```
Trial trial-0017 — val_bpb 1.207 (Δ -0.013 vs best, -0.027 vs baseline)
Mutation: increase DEPTH 8 → 10
- keep
- discard
- inspect-log
- refine-mutation (propose follow-up)
- stop-loop
```

### Step 5: Log

```bash
skills/autoresearch/scripts/log-experiment.sh \
  --project {name} \
  --trial-id trial-{NNNN} \
  --status {kept|discarded|failed} \
  --parent {parent_id} \
  --metric {value} \
  --mutation-summary "<one line>"
```

This script atomically:

- Appends a row to `experiments/log.md`
- Updates `state.json.trials.trial-NNNN`
- If `kept` and improves best → updates `state.json.leaderboard` and rewrites `leaderboard.md`
- Updates `memory/INDEX.md` last-modified timestamp

### Step 6: Compaction (every 10 trials or per phase exit)

Per [working-memory.md](../../../core/guides/working-memory.md):

- Refresh `memory/INDEX.md` (current best, last 5 trials, open hypotheses)
- Do **not** paste full run logs into orchestrator chat; reference paths

## Autonomous mode — subagent spawning

In `autonomous`:

1. Orchestrator runs Step 1 (kill-switch gate)
2. Spawns one [@autoresearch-experimenter](../../autoresearch-experimenter/SKILL.md) subagent
3. Subagent does Steps 2–5 and returns a structured report
4. Orchestrator updates state from the report, then loops to Step 1

**Parallelism:** Default **1 subagent at a time**. Trials are not independent — the next mutation depends on the current best. Parallel only when the user opts in (`context.parallelism: N`) and accepts that the leaderboard updates lag.

**Model:** Subagent inherits parent model — never `fast`. See [model-matrix.md](../../../core/guides/model-matrix.md).

## Tripwires (autonomous safety)

Configured in `context.safety.tripwires` (defaults shown):

| Tripwire | Default | Action |
|----------|---------|--------|
| Consecutive failures | 3 | Stop loop; route to Phase 4 with `status: aborted` |
| Metric NaN / Inf | 1 | Stop loop |
| Metric regresses ≥ 50% vs baseline 5 trials in a row | 5 | Stop loop |
| Wall-clock per trial exceeded by 2× | 1 | Stop loop |

Tripwires are checked by `check-kill-switch.sh` and `run-experiment.sh`.

## Phase advance

Exit the loop when any of:

- User chose `stop-loop` in `hitl`
- `max_trials` reached
- `max_total_wall_clock` exceeded
- Kill-switch / tripwire fired

Set `phase_status.loop: "completed"`, `current_phase: "autoresearch-4-synthesis"`.
