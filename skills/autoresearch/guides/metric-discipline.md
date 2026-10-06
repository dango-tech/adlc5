# Metric discipline

A bad metric is worse than no metric — it makes the loop confidently wrong. Read this before Phase 1 Step 3.

## The single-metric rule

**One scalar. One direction (min or max). Same computation for every trial.**

If you cannot pick one metric, the project is not ready for `@autoresearch`. Use `@discover` to clarify the problem first.

## What makes a metric fair

| Property | Why it matters |
|----------|----------------|
| **Deterministic given the artifact** | Same artifact → same metric (within documented noise). Seed your RNG; pin your eval set. |
| **Computable inside the per-trial budget** | If the metric takes longer than the budget, you'll measure noise. |
| **Independent of mutation flavor** | A metric that rewards depth-changes but punishes optimizer-changes is biased. |
| **Bounded noise** | Document the run-to-run variance (Phase 2 variance check). A trial's Δ must clear the noise band. |
| **Cheap to extract** | If extraction is itself flaky, fix it before trusting the loop. |

## Examples

### Good

| Metric | Why it works |
|--------|--------------|
| `val_bpb` on a **fixed** validation slice (karpathy) | Vocab-size independent; same slice every trial; deterministic with seed |
| Pass rate on a **frozen** eval set with same temperature & seed | Deterministic; clear scalar |
| p95 latency over a **fixed** workload with warmup discarded | Comparable; warmup discipline reduces noise |
| Recall@10 on a **labeled** query set | Bounded, well-defined, comparable |

### Bad

| Metric | Why it fails |
|--------|--------------|
| "Loss on whatever batch comes out" | Different batches across trials → noisy |
| "Latency on first request" | Cold-start dominates real signal |
| "Score on randomly sampled prompts" | Sample changes between trials |
| Pass rate with `temperature > 0` and no seed | Non-deterministic |
| Composite weighted sum of 5 things | Hides which thing moved |

## Guardrails (secondary signals — track, do not optimize)

Pick 1–3 guardrails with explicit thresholds. Examples:

- `cost_per_trial_usd < 0.10`
- `peak_memory_mb < 16000`
- `wall_clock_p95 < 6m`
- `api_error_rate < 1%`

A trial that wins the primary metric but breaches a guardrail is `discarded`. Document the breach in the trial row.

## Variance band — the minimum improvement threshold

After Phase 2, optionally run baseline 2–3× to estimate noise σ. Set `min_improvement` in `program.md`:

```
min_improvement = max(2σ, problem-specific tolerance)
```

A trial whose Δ vs current best is within `min_improvement` is `discarded` even if numerically lower (for `min`) or higher (for `max`). This kills noise-driven false wins.

## When the metric needs to change mid-loop

If you realize the metric was wrong:

1. **Stop the loop** (Phase 3 exit; do not silently change definitions)
2. Update intake (Phase 1 Step 3)
3. Rerun baseline (Phase 2)
4. Restart Phase 3 — previous trials are not comparable to the new metric

Document this in `report.md` Stop reason as "metric redefined".

## Anti-patterns

❌ Switching the metric mid-loop to make a favorite trial win  
❌ Reporting the **best of N** runs of a kept trial without disclosing the variance  
❌ Optimizing a proxy ("training loss") when the real target is downstream ("eval pass rate")  
❌ Letting evaluation share resources with training in a wall-clock budget — eval bias  
❌ Composite metrics without a fixed weighting and rationale
