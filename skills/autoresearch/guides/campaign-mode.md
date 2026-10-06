# Autoresearch — campaign mode

**Campaign mode is always on.** `@autoresearch` scaffolds `.autoresearch/{campaign}/` with shared framing and per-task experiment trees.

## Layout

```text
.autoresearch/{campaign}/
  state.json              # campaign phase machine
  framing.md
  tasks-index.md
  STOP                    # kill switch (optional)
  memory/
  tasks/
    {task-id}/
      state.json          # per-task phases 1–4
      program.md
      definition-of-done.md
      experiments/
      best-artifact/
```

## Phases

| Phase | ID | Scope |
|-------|-----|-------|
| Framing | `autoresearch-0-framing` | Campaign problem, link ADLC5 spec handoff |
| Decompose | `autoresearch-0b-decompose` | Split into parallelizable tasks; scaffold `tasks/{id}/` |
| Intake → Synthesis | `autoresearch-1` … `4` | Per task — same invariants as single-project mode |

## ADLC5 link

When Specify completes (`specify-4-handoff`), optional handoff sets:

- `adlc5_feature` — kebab-case feature name
- `spec_handoff_path` — e.g. `.adlc5/{feature}/spec-handoff.md`

Framing phase reads the handoff for problem summary and acceptance criteria.

## Definition of done

Default: **`budget_exhausted`**. On every loop exit (kill-switch or budget), run **AskQuestion** per [askquestion-convention.md](../../../core/guides/askquestion-convention.md):

| `id` | Label |
|------|-------|
| `dod_budget_exhausted` | Budget exhausted — stop task loop |
| `dod_metric_plateau` | Metric plateau — stop task loop |
| `dod_target_met` | Target metric met — stop task loop |
| `dod_continue` | Continue with extended budget |

Record selection in task `definition-of-done.md` and `state.json`.

## Scripts

| Script | Role |
|--------|------|
| `init-campaign.sh` | Scaffold campaign root |
| `init-task.sh` | Scaffold one task under `tasks/{id}/` |
| `init-project.sh` | Campaign + default task `main` |
| `lib/resolve-autoresearch-dir.sh` | Used by run/log/kill-switch scripts |

Experiment scripts accept `--project {campaign}` and `--task {task_id}` (default `main`).
