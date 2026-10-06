# Definition of done — task `{task_id}`

**Campaign:** {campaign_name}  
**Default exit:** `budget_exhausted` (confirm via AskQuestion on every loop exit)

---

## Exit criteria (pick one per run — AskQuestion required)

| ID | Criterion | When satisfied |
|----|-----------|----------------|
| `budget_exhausted` | Trial or wall-clock budget hit | `check-kill-switch.sh` exits non-zero for budget |
| `metric_plateau` | No improvement in last N trials | Document N and threshold in task `program.md` |
| `target_met` | Metric crosses declared target | User confirms target in intake |
| `manual_stop` | User STOP file or explicit halt | Kill switch or user choice |

---

## Record on exit

Update `tasks/{task_id}/state.json`:

- `phase_status.loop: "completed"`
- `definition_of_done.selected: "<id>"`
- `definition_of_done.confirmed_at: "<iso8601>"`

Then route to Phase 4 synthesis for the task.
