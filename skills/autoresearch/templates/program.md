# program.md — Autoresearch instructions for {project_name}

> **What this is:** The thin "research org" skill that the experimenter reads on every trial. Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch). Edit this file to steer the loop; the experimenter does not read state.json or the orchestrator's chat.

## Target

- **Artifact (mutable, single file):** `{artifact_path}`
- **Supporting files (read-only):** `{supporting_files}`
- **Execute command:** `{execute_cmd}`
- **Metric:** `{metric_name}` — direction `{min|max}` — extracted via `{metric_extract_cmd}`

## Budget

- **Per trial:** `{per_trial_budget}` (wall-clock | step-count | dataset-pass — pick one)
- **Max trials this session:** `{max_trials}`
- **Total wall-clock cap:** `{max_total_wall_clock}`

## Stop conditions

- **Kill switch:** `{kill_switch_path}` — touch this file from any shell to stop the loop after the current trial
- **Cost cap:** `{cost_cap_usd}` (USD; null = no cap)
- **Tripwires:** stop on 3 consecutive failed trials, NaN/Inf metric, or 5 trials regressing ≥ 50% vs baseline

## File boundaries (hard)

The experimenter may **only** modify `{artifact_path}` and files inside the active trial's `experiments/trial-NNNN/` directory. Any write outside these paths is a blocker — stop and report.

Do not modify:

- `prepare.py` / data preparation
- Eval harness
- This `program.md`
- `state.json`, `leaderboard.md`, `report.md`
- Anything in `.git/`

## Mutation policy

- **One mutation per trial.** Pick the highest-leverage cheap change first (see [mutation-strategies.md](../guides/mutation-strategies.md)).
- **Record `mutation_summary`** in ≤ 120 chars before running.
- **Stop a cluster after 3 consecutive losses** — pivot dimension.
- **Single-metric rule** — guardrails are tracked, not optimized. Current guardrails:

| Guardrail | Threshold | Action if breached |
|-----------|-----------|--------------------|
| `cost_per_trial_usd` | `< 0.10` | Discard trial |
| `peak_memory_mb` | `< {memory_cap}` | Discard trial |
| (add others here) | — | — |

## Per-trial protocol (what the experimenter does)

1. Read this `program.md` and the current leaderboard top row
2. Read the parent artifact at `experiments/{parent_trial_id}/artifact.<ext>`
3. Propose **one** mutation; write the mutated artifact into the current trial dir
4. Write `mutation_summary.txt` (one line)
5. Invoke `scripts/run-experiment.sh` — script enforces budget
6. Read `metric.txt` from the trial dir; compare to current best
7. Return a structured report to the orchestrator (keep / discard / failed + rationale)
8. The orchestrator (not the experimenter) updates state and leaderboard

## Reproducibility

Every kept trial must be reproducible from the snapshot in `experiments/{trial_id}/`. Record:

- Random seed (if applicable)
- Key dependency versions printed at run start
- Hardware / runtime if it affects the metric

## Notes (human-edited)

(Use this section to steer the loop: open hypotheses, dimensions to try next, observations about variance, known dead ends. The experimenter reads this every trial.)

- …
