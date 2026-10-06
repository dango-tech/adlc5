# Autopilot stage picker

Use with **AskQuestion** when `@adlc5` starts. **Stage scope is never silent** — even when `interaction_mode: autonomous`, the user must confirm which substeps run.

## Lifecycle tree

```text
Stage 1 — Specify
  specify-0-git → specify-1-discover (optional) → specify-2-requirements → specify-3-nfr → specify-4-handoff

Stage 2 — Plan
  plan-1-engineering-architecture → plan-2-engineering-patterns → plan-3-engineering-algorithms
  → plan-4-design-discovery → plan-5-design-contracts → plan-6-design-operations → plan-7-design-critique

Stage 3 — Tasks
  tasks-1-stories → tasks-2-code-spec

Stage 4 — Implement
  implement-1-build → implement-2-verify → implement-3-integrate → implement-4-qa → implement-5-pr
```

## Autonomous routing matrix (`@adlc5`)

Requires `.adlc5/{feature}/policies.yaml` with `autopilot` section.

| Substep | Skill | Policy field | Skip when |
|---------|-------|--------------|-----------|
| Specify | `@adlc5-specify` | profile | skipped substeps follow selected profile |
| Plan | `@adlc5-plan` | profile | tiny records decisions in change.md; standard retains brief design/plan.md |
| Tasks | `@adlc5-tasks` | profile | tiny profile |
| Design critic | `@adlc5-design-critic` | `interaction_mode: autonomous` | only after a non-blocking critique |
| Implement build | `@build-implementer` via `@adlc5-implement` | `execution_mode` | |
| Implement verify | `@assure-verifier` via `@adlc5-implement` | `verify_policy: auto` | profile policy |
| Implement integrate | `@adlc5-implement` | `integrate_policy: auto` | profile policy |
| Implement QA | `@qa` | required by high-risk profile | profile policy |
| Implement PR | `@pr-reviewer` | **always for pr_ready** | **never** |

## Resume from any stage

| `autopilot.resume_from` | Behavior |
|-------------------------|----------|
| `null` | Start at canonical `current_step` (default) |
| `current_step` | Explicit alias of canonical lifecycle state |
| Step ID (e.g. `implement-4-qa`) | Run selected substeps through `stop_at_phase` |

**Rules:**

1. Do not advance past `autopilot.stop_at_phase` without AskQuestion.
2. Endpoint `pr_ready` requires every gate enabled by the selected profile.
3. Re-invoking `@adlc5` reads `.adlc5/{feature}/state.json` and `policies.yaml`; deterministic gates remain idempotent.

## AskQuestion prompts (mandatory)

### `@adlc5` start

1. `interaction_mode` — `hitl` | `autonomous` (session scope)
2. `autopilot_substeps` — multi-select from tree above OR `none`
3. `target_outcome` — `resume_current` | `advance_one_stage` | `run_to_pr_ready`

Autonomous mode uses the same questions and lifecycle state; there is no separate pilot invocation.

Map option IDs to `state.json` / `policies.yaml` per the [AskQuestion convention](https://github.com/dango-tech/adlc5/blob/main/core/guides/askquestion-convention.md).
