# Autoresearch report — {project_name}

**Best trial:** `{best_trial_id}`
**Metric:** `{metric_name} = {best_metric_value}` ({metric_direction})
**Δ vs baseline:** `{delta_vs_baseline}`
**Total trials:** `{total_trials}` ({kept_count} kept, {discarded_count} discarded, {failed_count} failed)
**Total wall clock:** `{total_wall_clock}`
**Stop reason:** `{stop_reason}` (budget | user-stop | kill-switch | tripwire | metric-redefined)

---

## Target

- **Artifact:** `{artifact_path}`
- **Metric:** `{metric_name}` — direction `{min|max}`
- **Budget per trial:** `{per_trial_budget}`
- **Execute command:** `{execute_cmd}`

## Leaderboard — top 10

| Rank | Trial | Metric | Δ vs baseline | Parent | Mutation |
|------|-------|--------|---------------|--------|----------|
| 1 | {best_trial} | … | … | … | … |
| 2 | … | … | … | … | … |

## Best artifact

- Path: `.autoresearch/{project}/best-artifact/`
- Diff vs baseline: `.autoresearch/{project}/best-artifact/diff-vs-baseline.patch`
- Run log: `.autoresearch/{project}/best-artifact/run.log`

## What worked

- (Pattern 1 — short rationale + evidence trial ids)
- (Pattern 2 — …)

## What did not work

- (Anti-pattern 1 — trials)
- (Anti-pattern 2 — …)

## Open hypotheses

Mutations the loop did not get to; worth trying next session.

- (Hypothesis 1)
- (Hypothesis 2)

## Reproducibility

```bash
# From a clean checkout of {project_name}:
git checkout {commit_hash}
cp .autoresearch/{project_name}/best-artifact/artifact.<ext> {artifact_path}
{execute_cmd}
{metric_extract_cmd}
# Expected: {metric_name} ≈ {best_metric_value} (± noise band σ = {noise_sigma})
```

Environment:

- Runtime: `{runtime_version}` (e.g. `python 3.11.x`, `uv 0.5.x`)
- Key deps: `{key_deps}`
- Hardware: `{hardware_notes}`
- Seed: `{seed}`

## Guardrails

| Guardrail | Threshold | Best trial value | Status |
|-----------|-----------|------------------|--------|
| `cost_per_trial_usd` | `< 0.10` | … | ok |
| `peak_memory_mb` | `< 16000` | … | ok |

## Notes

(Free-form observations — variance bands, sensitivity to seed, suggestions for next session.)
