# Memory INDEX — {project_name}

**Feature:** {project_name}
**Current phase:** {current_phase}
**Last compacted:** {last_compacted}
**Updated:** {iso8601}

## Active phase summary

(Phase summary lives at `memory/summaries/{phase}.md` once written; reference here only.)

| Artifact | Phase | Summary |
|----------|-------|---------|
| `.autoresearch/{project_name}/program.md` | intake | Target + budget + safety contract |
| `.autoresearch/{project_name}/experiments/baseline/run.log` | baseline | Baseline metric = {baseline_metric} |
| `.autoresearch/{project_name}/leaderboard.md` | loop | Current best: {best_trial_id} ({best_metric}) |
| `.autoresearch/{project_name}/report.md` | synthesis | (written in Phase 4) |

## Loop snapshot (last 5 trials)

| Trial | Mutation | Metric | Decision |
|-------|----------|--------|----------|
| … | … | … | … |

> Compact this INDEX every 10 trials or at every phase exit. See [working-memory.md](../../../core/guides/working-memory.md).
