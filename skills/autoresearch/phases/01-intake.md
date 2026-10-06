---
name: autoresearch-intake
description: Phase 1 — Project Intake. Define mutable artifact, metric, budget, baseline command. Produces program.md from template.
---

# Phase 1 — Project Intake

## Purpose

Lock down the four invariants that make trials fair and the loop coherent:

1. **Mutable artifact** — the single file the experimenter is allowed to edit
2. **Metric** — one scalar with a direction (min / max)
3. **Budget per trial** — wall clock, step count, or dataset pass
4. **Execute command** — how to run the artifact and emit the metric

A vague intake produces an unrunnable loop. Invest time here.

## Entry

**Campaign mode:** Read `tasks/{task_id}/state.json` (not campaign root). `task_id` = campaign `active_task_id` or user-selected task.

If `state.json.phase_status.intake` is already `completed`, skip to Phase 2 unless the user explicitly resumes intake.

## Interview (use AskQuestion for choices; chat for free text)

> Per [askquestion-convention.md](../../../core/guides/askquestion-convention.md): use AskQuestion for finite choices, batch up to 2 per call.

### Step 1: Target shape

**AskQuestion** — `target_shape` (one of):

- `ml-training` — single-file ML loop (karpathy default)
- `prompt-tuning` — prompt/instructions vs eval set
- `retrieval-tuning` — retriever config vs labeled queries
- `algorithm-perf` — implementation file vs latency / throughput
- `hyperparam-search` — config file vs scalar metric
- `custom` — describe in chat

Each option pre-fills defaults in Step 2 from [guides/mutation-strategies.md](../guides/mutation-strategies.md).

### Step 2: Mutable artifact (chat)

```
"Which single file or config will the experimenter edit?
- Absolute or repo-relative path (e.g. `train.py`, `prompts/agent.md`, `config/retrieval.yaml`)
- Must be self-contained — no companion files the agent must also edit
- If you have non-mutable supporting files (data prep, eval harness), list them now"
```

Store as `context.target.artifact_path` and `context.target.supporting_files`.

### Step 3: Metric (AskQuestion + chat)

**AskQuestion** — `metric_direction`: `min` (lower better, e.g. loss/latency) | `max` (higher better, e.g. accuracy/recall).

Chat — confirm:

- `metric_name` (e.g. `val_bpb`, `pass_rate`, `p95_latency_ms`)
- `metric_extract_cmd` — how to extract the scalar from the run output (script path or pipe)
- One sentence on what makes the metric **fair** (e.g. "computed on a fixed validation set, vocab-size-independent")

> **Single-metric rule:** Track secondary signals (cost, latency, memory) as **guardrails** with thresholds, not as optimization targets. Document them in the program.md template.

### Step 4: Budget (AskQuestion)

`budget_mode`: `wall-clock` | `step-count` | `dataset-pass`.

Then chat:

- `per_trial` (e.g. `5m`, `1000 steps`, `200 items`)
- `max_trials` (default 50)
- `max_total_wall_clock` (default `8h`)

Karpathy's default — `wall-clock` `5m`, ~12 trials/hr, ~100 trials/night.

### Step 5: Execute command (chat)

```
"What command runs the artifact end-to-end and emits the metric?
- One shell command, idempotent given a snapshotted artifact
- Should exit non-zero on failure
- Should print the metric to stdout in a parseable form (or write to a known file)
Examples:
  uv run train.py
  pytest -q tests/eval_prompt.py --json-report
  python bench.py --config retrieval.yaml > metric.json"
```

Store as `context.target.execute_cmd`.

### Step 6: Safety + interaction mode (AskQuestion)

Confirm or override defaults from `init-project.sh`:

| `id` | Maps to | Default |
|------|---------|---------|
| `interaction_mode` | `context.interaction_mode` | `hitl` |
| `kill_switch_path` | `context.safety.kill_switch_path` | `.autoresearch/{project}/STOP` |
| `cost_cap_usd` | `context.safety.cost_cap_usd` | `null` (no cap) — only relevant for paid API calls inside the trial |

See [guides/safety-and-budget.md](../guides/safety-and-budget.md).

## Output — `program.md`

Render the template at [templates/program.md](../templates/program.md), filling intake answers. This is the **thin skill** the experimenter reads on every trial — the karpathy invariant.

The orchestrator writes `.autoresearch/{project}/program.md` and shows the user the rendered file for approval before Phase 2.

## Quality checklist (before phase advance)

- [ ] Exactly one mutable artifact path; supporting files explicitly listed and read-only
- [ ] Exactly one metric with direction; extract command runnable
- [ ] Budget is finite and machine-checkable
- [ ] Execute command runs the baseline locally (do not assume — Phase 2 will smoke-test it)
- [ ] `program.md` written and approved by user
- [ ] Kill-switch path documented

## Phase advance (AskQuestion)

```
Phase 1 — Intake complete. Ready for Phase 2 — Baseline & Smoke Test?
- yes — continue to baseline
- revise — change intake answers
- pause — resume later
```

Set `phase_status.intake: "completed"`, `current_phase: "autoresearch-2-baseline"`.
