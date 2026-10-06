---
name: autoresearch-synthesis
description: Phase 4 — Synthesis & Report. Produce report.md with best config, leaderboard, learnings, reproducibility info. Optional handoff to @adlc5 or @qa.
---

# Phase 4 — Synthesis & Report

## Purpose

Convert the trial log into a **decision-grade artifact** — the best mutated file, a leaderboard the user can defend, what was tried that did not work, and how to reproduce the best result.

Without Phase 4, the loop produces a folder of trials with no narrative — useful to nobody.

## Entry

Pre-conditions:

- `phase_status.loop: "completed"` (any exit reason: budget, user stop, kill-switch)
- `leaderboard.md` exists with ≥ 1 row beyond baseline (or baseline-only with documented reason for stopping)

## Outputs

### 1. `report.md` (primary artifact)

Path: `.autoresearch/{project}/report.md`. Use [templates/report.md](../templates/report.md). Sections:

| Section | Content |
|---------|---------|
| Summary | Best trial id, metric value, Δ vs baseline, total trials run, total wall clock |
| Target | Artifact, metric, budget, execute command (from intake) |
| Leaderboard (top 10) | Same shape as `leaderboard.md` |
| Best artifact | Path to `experiments/{best}/artifact.<ext>` + diff vs baseline |
| What worked | 1–3 bullets — patterns of mutations that improved metric |
| What did not work | 1–3 bullets — patterns that hurt or were neutral |
| Open hypotheses | Mutations the loop did not get to; would try next |
| Reproducibility | Commands to reproduce the best trial from scratch (commit hash, env, seed if applicable) |
| Guardrails | Secondary signals tracked (cost, latency, memory) and any threshold breaches |
| Stop reason | Why the loop ended (budget / user / tripwire / kill-switch) |

### 2. `best-artifact/`

Copy `experiments/{best_trial_id}/` to `.autoresearch/{project}/best-artifact/` (flat, easy to find). Include `run.log` so users can verify the metric independently.

### 3. Memory summary

Write `memory/summaries/autoresearch.md` per [working-memory.md](../../../core/guides/working-memory.md): top-level decisions, best metric, paths.

## Process

### Step 1: Aggregate

The orchestrator reads `state.json.trials` and `leaderboard.md`. No need to re-read run logs — the leaderboard and per-trial metric values are authoritative.

### Step 2: Pattern extraction

Cluster trials by `mutation_summary` keywords (depth, optimizer, prompt-wording, etc.) and look for:

- **Wins concentrated in one cluster** → likely real effect, worth documenting
- **High variance within a cluster** → noisy effect, mark as inconclusive
- **Consistent losses in another cluster** → "do not try" learning

Keep this to 3–5 bullets each in `report.md`. Resist long prose.

### Step 3: Reproducibility check

For the best trial:

- Confirm `experiments/{best}/artifact.<ext>` exists and matches the leaderboard metric (re-extract from `run.log` if needed)
- Capture environment: git commit hash at session start (already in `state.json`), interpreter version, key dependency versions
- Write reproducibility commands in `report.md`

> **Optional verification run:** If `autonomous` mode and budget allows, run the best trial once more from scratch to confirm the metric within noise. Document the spread.

### Step 4: Handoff (AskQuestion)

```
Phase 4 — Report ready at .autoresearch/{project}/report.md
Best: trial-NNNN, {metric}={value} (Δ {delta} vs baseline)
Next step?
- finish — stop here
- ship-via-adlc5 — hand best artifact + report to @adlc5-specify as input
- ship-via-qa — route best artifact + tests through @qa for deployment-clearance
- continue-loop — relax budget and run more trials (back to Phase 3)
```

### Step 5: Memory + state

- `phase_status.synthesis: "completed"`
- `current_phase: "completed"`
- Append summary path to `memory/INDEX.md`

## Quality checklist

- [ ] `report.md` rendered from template with all sections
- [ ] `best-artifact/` populated and matches leaderboard top row
- [ ] Reproducibility commands runnable from clean checkout
- [ ] Stop reason documented honestly (do not paper over kill-switch / regression)
- [ ] Memory summary written and INDEX updated
- [ ] Handoff choice captured in state

## Anti-patterns

❌ Cherry-pick a non-best trial because the story is nicer  
❌ Re-run the best trial silently until it improves (drift inflates apparent win)  
❌ Bury the stop reason — "budget exhausted with no improvement" is a valid honest outcome  
❌ Paste full run logs into report — link by path
