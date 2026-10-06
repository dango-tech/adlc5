---
name: autoresearch
description: Autoresearch — autonomous experimentation loop for any iterable target (ML training, prompt tuning, algorithm tuning, latency optimization). Single mutable artifact, fixed budget per run, single metric, accept/reject with leaderboard. Foundation - https://github.com/karpathy/autoresearch. Use when the user wants to run an autonomous iteration loop.
version: 1.0.0
author: ADLC5 Contributors
---

# Autoresearch — Autonomous Experimentation Loop

## Intent

**Autoresearch** runs a structured **edit → measure → accept/reject** loop on a single mutable artifact against a single scalar metric within a fixed per-run budget. It generalizes the [karpathy/autoresearch](https://github.com/karpathy/autoresearch) idea — autonomous overnight ML experimentation — to any domain where the work fits the same shape: one file/config to mutate, one number to optimize, one fixed budget per trial.

**User invokes:** `@autoresearch for [campaign-name]` (always **campaign mode** — see [guides/campaign-mode.md](guides/campaign-mode.md))

**Examples of fit:**

| Target | Mutable artifact | Metric | Budget per trial |
|--------|-------------------|--------|------------------|
| Single-GPU LLM training (karpathy default) | `train.py` | `val_bpb` (lower better) | 5 min wall clock |
| Prompt optimization | `prompt.md` | Eval-set pass rate | N test items |
| Retrieval (RAG) tuning | `retriever.yaml` | Recall@k on labeled set | 200 queries |
| Algorithm hot path | `module.py` | p95 latency (ms) | 60 s benchmark |
| Hyperparameter search | `config.yaml` | Custom scalar | Fixed step count |

**Out of scope:** Multi-metric Pareto optimization, multi-file architectural refactor, work that requires human design judgment per iteration. Use `@adlc5-plan` for design-led work; use autoresearch for **search**.

---

## Anchors

**Foundation:** [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — `program.md` as a thin skill, single editable file, fixed time budget, one metric. See [guides/knowledge-base.md](guides/knowledge-base.md) for verbatim mapping.

**ADLC5 fit:**

- Sibling pipeline to `@discover`, `@prt`, `@qa` — not part of `@adlc5` lifecycle by default
- Honors [interaction-modes.md](../../core/guides/interaction-modes.md): `hitl` confirms each trial; `autonomous` runs the loop to budget
- Honors [model-matrix.md](../../core/guides/model-matrix.md): orchestrator `balanced`; experimenter subagent inherits parent
- Scripts over skill logic per [adlc5-sdd-mantra](../../.cursor/rules/adlc5-sdd-mantra.mdc) — repeatable work lives in [scripts/](scripts/)

**Working memory:** `.autoresearch/{campaign}/memory/` — INDEX + per-task summaries. See [core/guides/working-memory.md](../../core/guides/working-memory.md).

**ADLC5 hook:** After Specify handoff (`specify-4-handoff`), optional handoff starts a campaign linked to `.adlc5/{feature}/spec-handoff.md`.

---

## Phases (campaign)

| Phase ID | Display label | Scope | Phase doc |
|----------|---------------|-------|-----------|
| `autoresearch-0-framing` | Campaign framing | Campaign | [phases/00-framing.md](phases/00-framing.md) |
| `autoresearch-0b-decompose` | Task decomposition | Campaign | [phases/00b-decompose.md](phases/00b-decompose.md) |
| `autoresearch-1-intake` | Task intake | Per task | [phases/01-intake.md](phases/01-intake.md) |
| `autoresearch-2-baseline` | Baseline & smoke | Per task | [phases/02-baseline.md](phases/02-baseline.md) |
| `autoresearch-3-loop` | Experiment loop | Per task | [phases/03-experiment-loop.md](phases/03-experiment-loop.md) |
| `autoresearch-4-synthesis` | Synthesis & report | Per task | [phases/04-synthesis.md](phases/04-synthesis.md) |

**Subagent:** [autoresearch-experimenter](../autoresearch-experimenter/SKILL.md) — runs one trial (edit → execute → measure) and returns a structured report. Spawned per trial in `autonomous` mode; optional in `hitl`.

---

## Workspace setup

### On first invocation

1. **Extract campaign name** from request (kebab-case). If unclear, **AskQuestion** for a name.
2. **Check state:** Read `.autoresearch/{campaign}/state.json` (`mode` must be `campaign`).
3. **If state missing:**
   - Run `skills/autoresearch/scripts/init-campaign.sh --campaign {name} --workspace .`  
     (or `init-project.sh` — wraps campaign + default task `main`)
   - Set `current_phase: "autoresearch-0-framing"`.
   - Collect preferences via **AskQuestion** (see below).
   - Route to Phase 0.
4. **If state exists:**
   - Read `memory/INDEX.md`; resume from `current_phase`.
   - For phases 1–4, use **task state** at `tasks/{task_id}/state.json` (`active_task_id` on campaign state).
5. **From ADLC5 Specify handoff:** pass `--adlc5-feature {feature}` and `--spec-handoff .adlc5/{feature}/spec-handoff.md` to `init-campaign.sh`.

### Initial preferences (AskQuestion)

Use [askquestion-convention.md](../../core/guides/askquestion-convention.md). Batch up to 2 per call.

| `id` | Maps to | Options |
|------|---------|---------|
| `interaction_mode` | `context.interaction_mode` | `hitl` / `autonomous` |
| `budget_mode` | `context.budget.mode` | `wall-clock` / `step-count` / `dataset-pass` |
| `qa_log` | `context.save_qa_log` | yes / no |
| `safety_kill_switch` | `context.safety.kill_switch_path` | default `.autoresearch/{campaign}/STOP` / custom |

Defaults — `interaction_mode: hitl`, `budget_mode: wall-clock`, `qa_log: yes`.

---

## State files

**Campaign** — `.autoresearch/{campaign}/state.json` (see [templates/campaign-state.json](templates/campaign-state.json))

**Task** — `.autoresearch/{campaign}/tasks/{task_id}/state.json` (see [templates/task-state.json](templates/task-state.json))

Legacy single-project fields (task scope):

```json
{
  "project_name": "string",
  "current_phase": "autoresearch-1-intake",
  "phase_status": {
    "intake": "pending|in_progress|completed",
    "baseline": "pending|in_progress|completed",
    "loop": "pending|in_progress|completed",
    "synthesis": "pending|in_progress|completed"
  },
  "context": {
    "interaction_mode": "hitl|autonomous",
    "save_qa_log": true,
    "budget": {
      "mode": "wall-clock|step-count|dataset-pass",
      "per_trial": "5m | 1000 steps | 200 items",
      "max_trials": 50,
      "max_total_wall_clock": "8h"
    },
    "safety": {
      "kill_switch_path": ".autoresearch/{project}/STOP",
      "cost_cap_usd": null,
      "tripwires": []
    },
    "target": {
      "artifact_path": "train.py",
      "mutable_only": true,
      "execute_cmd": "uv run train.py",
      "metric_name": "val_bpb",
      "metric_direction": "min|max",
      "metric_extract_cmd": "scripts/extract_metric.sh"
    }
  },
  "baseline": {
    "metric_value": null,
    "trial_id": null,
    "captured_at": null
  },
  "trials": {
    "trial-0001": {
      "status": "running|kept|discarded|failed",
      "parent_trial_id": "baseline",
      "mutation_summary": "string",
      "metric_value": 1.23,
      "delta_vs_best": -0.04,
      "started_at": "ISO8601",
      "ended_at": "ISO8601",
      "artifact_snapshot": "experiments/trial-0001/train.py",
      "log_path": "experiments/trial-0001/run.log"
    }
  },
  "leaderboard": {
    "best_trial_id": "trial-0017",
    "best_metric_value": 1.07,
    "updated_at": "ISO8601"
  },
  "memory": {
    "index_path": ".autoresearch/{project}/memory/INDEX.md",
    "last_compacted": null
  }
}
```

---

## Artifacts

| Path | Purpose |
|------|---------|
| `.autoresearch/{campaign}/framing.md` | Campaign problem + ADLC5 handoff summary |
| `.autoresearch/{campaign}/tasks-index.md` | Task registry |
| `.autoresearch/{campaign}/tasks/{id}/program.md` | Experimenter instructions (per task) |
| `.autoresearch/{campaign}/tasks/{id}/definition-of-done.md` | Exit criteria; default `budget_exhausted` |
| `.autoresearch/{campaign}/tasks/{id}/leaderboard.md` | Ranked trials per task |
| `.autoresearch/{campaign}/tasks/{id}/experiments/trial-NNNN/` | Per-trial snapshot |
| `.autoresearch/{campaign}/STOP` | Kill-switch for whole campaign |

---

## Scripts (called by skills — do not paste inline shell into phase prompts)

| Script | Purpose |
|--------|---------|
| [scripts/init-campaign.sh](scripts/init-campaign.sh) | Scaffold campaign root |
| [scripts/init-task.sh](scripts/init-task.sh) | Scaffold `tasks/{id}/` |
| [scripts/init-project.sh](scripts/init-project.sh) | Campaign + default task `main` |
| [scripts/run-experiment.sh](scripts/run-experiment.sh) | Snapshot artifact, run `execute_cmd` with budget, capture log + exit code |
| [scripts/log-experiment.sh](scripts/log-experiment.sh) | Append trial to log.md, update leaderboard.md, write `state.json.trials.*` |
| [scripts/check-kill-switch.sh](scripts/check-kill-switch.sh) | Exit non-zero if STOP file present or budget exceeded |

Per the [ADLC5 SDD Mantra](../../.cursor/rules/adlc5-sdd-mantra.mdc): all repeatable actions live in scripts; this skill's job is **when** to call them, with **what** arguments.

---

## Safety and budget (mandatory)

Read [guides/safety-and-budget.md](guides/safety-and-budget.md) before starting Phase 3 in `autonomous` mode.

- **Per-trial budget** caps a single run (wall clock / step count / dataset pass)
- **Total budget** caps the whole session (`max_trials`, `max_total_wall_clock`)
- **Kill switch** — `STOP` file in project root, checked between every trial
- **Cost cap** — abort if cumulative API/compute cost exceeds `cost_cap_usd`
- **Tripwires** — abort on regressions worse than configured threshold (e.g. metric NaN, OOM, exit code != 0 N times in a row)

**`hitl` mode** confirms each trial via AskQuestion (keep / discard / mutate). **`autonomous`** runs unattended within budget; orchestrator must call `check-kill-switch.sh` between trials.

---

## Routing rules

**Do:**

- Always run the loop on **one mutable artifact** with **one metric**
- Snapshot before every trial; never overwrite the parent without a kept decision
- Update `leaderboard.md` immediately when a trial is kept
- Call scripts for repeatable work (run, log, kill-switch); orchestrator decides what to mutate

**Do not:**

- Run multi-artifact refactors here (use `@adlc5-plan`)
- Optimize multiple metrics simultaneously (pick one; track others as guardrails)
- Skip baseline (Phase 2) — every trial must be comparable
- Continue after kill-switch trips, even one trial more

---

## Handoff

When Phase 4 completes, the agent emits `.autoresearch/{project}/report.md` summarizing best config, leaderboard, and reproducibility info. Optional handoffs:

- **To `@adlc5`** — if the winning config implies a feature change worth shipping, hand the best artifact + report to `@adlc5-specify` as input
- **To `@qa`** — if the winning config is production-bound, route artifact + tests through `@qa` for the deployment-clearance gate

Autoresearch itself does not modify production code; it produces a recommended artifact and evidence.
