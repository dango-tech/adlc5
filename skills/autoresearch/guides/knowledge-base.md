# Autoresearch — Knowledge base

## Foundation

[karpathy/autoresearch](https://github.com/karpathy/autoresearch) — *"AI agents running research on single-GPU nanochat training automatically."*

> The idea: give an AI agent a small but real LLM training setup and let it experiment autonomously overnight. It modifies the code, trains for 5 minutes, checks if the result improved, keeps or discards, and repeats.
> — karpathy/autoresearch README

This adlc5 skill **generalizes** that idea (one file, one metric, fixed budget, accept/reject) to any target shape; the ML-training case remains the reference flavor.

## Core invariants (do not violate)

| Invariant | Why |
|-----------|-----|
| **Single mutable file** | Keeps scope manageable and diffs reviewable. Multi-file change = unattributable result. |
| **Fixed budget per trial** | Wall clock / step count / dataset pass. Makes trials directly comparable regardless of mutation cost. |
| **Single metric with direction** | Multi-metric optimization is human design work, not search. Track others as guardrails only. |
| **Baseline before mutations** | No baseline → no leaderboard → no decision. Phase 2 is mandatory. |
| **Single mutation per trial** | Two changes per trial cannot be attributed. The loop relies on attribution. |
| **Snapshot before run** | Parent is preserved; rollback is free; reproducibility is implicit. |

## Mapping karpathy → adlc5

| karpathy/autoresearch | adlc5 autoresearch |
|-----------------------|---------------------|
| `program.md` (thin skill for one agent) | [templates/program.md](../templates/program.md) — written by user during intake, read by experimenter every trial |
| `train.py` (sole editable file) | `context.target.artifact_path` |
| `prepare.py` (constants, dataloader, eval) | `context.target.supporting_files` — read-only |
| Fixed **5-min wall clock** | `context.budget` — `wall-clock` / `step-count` / `dataset-pass` |
| `val_bpb` (lower better, vocab-independent) | `context.target.metric_name` + `metric_direction` |
| Agent runs autonomously overnight | `context.interaction_mode: "autonomous"` with kill-switch and tripwires |
| "Disable all permissions" advice | Replaced with explicit kill-switch + cost cap + tripwires — see [safety-and-budget.md](safety-and-budget.md) |
| Single H100 GPU | Compute target documented in `program.md`; not enforced by skill |
| Notable forks (MacOS, MLX, Windows, AMD) | `target_shape` choice in intake; `program.md` captures platform notes |

## Design choices preserved verbatim

From the karpathy README:

1. **Single file to modify** — kept. Multi-file refactors belong in `@adlc5-plan`.
2. **Fixed time budget** — kept; generalized to non-time budgets where appropriate.
3. **Self-contained** — kept; no external orchestrator dependency. Scripts are bash; no daemon.

## Differences from karpathy/autoresearch (intentional)

| Topic | karpathy | adlc5 |
|-------|----------|--------|
| Permissions | "disable all permissions" — personal research mode | Default `hitl`; `autonomous` requires explicit opt-in + kill-switch + tripwires |
| Domain | LLM training specifically | Domain-agnostic; ML training is one `target_shape` |
| Logging | Implicit via experiments folder | Structured `experiments/log.md` + `state.json.trials` + `leaderboard.md` |
| Reproducibility | Documented in commits | Mandatory `report.md` section in Phase 4 |
| Handoff | "Wake up to a log" | Optional `@adlc5` / `@qa` handoff for production use |

## When to use autoresearch vs other adlc5 skills

| Need | Skill |
|------|-------|
| Search a hyperparameter / config / prompt space against one metric | **`@autoresearch`** |
| Design a new feature with multiple files and human judgment | `@adlc5` → `@adlc5-plan` |
| Validate production readiness | `@qa` |
| Problem framing + solution exploration | `@discover` |
| Multi-LLM perspective on a design question | `@discover` Phase 1 (LLM council) |

## Suggested reading order

1. [karpathy/autoresearch README](https://github.com/karpathy/autoresearch) — the source idea
2. [SKILL.md](../SKILL.md) — adlc5 orchestrator
3. [metric-discipline.md](metric-discipline.md) — what counts as a fair metric
4. [mutation-strategies.md](mutation-strategies.md) — what to change per trial
5. [safety-and-budget.md](safety-and-budget.md) — running unattended without burning the house down
