---
name: autoresearch-decompose
description: Phase 0b — Decompose campaign into parallelizable experiment tasks under tasks/{id}/.
---

# Phase 0b — Decompose into tasks

## Purpose

Split the campaign into **independent** experiment tasks. Each task owns one mutable artifact, one metric, and phases 1–4 under `tasks/{task-id}/`.

## Entry

- `phase_status.framing: "completed"`
- `phase_status.decompose` is not `completed`

## Steps

### 1. Propose task list (chat)

From [framing.md](../templates/framing.md), propose 2–`max_tasks` tasks. Each task needs:

- `task_id` (kebab-case)
- One-line title
- Mutable artifact candidate (path or type)
- Metric hint (name + direction)

**AskQuestion** — `task_list_confirm`: `approve` / `revise` / `add_task`

### 2. Scaffold each task

For each approved `task_id`:

```bash
skills/autoresearch/scripts/init-task.sh \
  --campaign {campaign} --task {task_id} --workspace .
```

Updates campaign `state.json.tasks[task_id]` with `status: "pending"`, `current_phase: "autoresearch-1-intake"`.

### 3. Update tasks-index.md

Fill [templates/tasks-index.md](../templates/tasks-index.md) at campaign root.

### 4. State update

```json
{
  "current_phase": "autoresearch-1-intake",
  "phase_status": { "decompose": "completed", "tasks": "in_progress" },
  "active_task_id": "<first-task-id>"
}
```

## Execution order

- **Sequential (default):** Complete phases 1–4 for `active_task_id`, then advance to next pending task.
- **Parallel (autonomous only):** Spawn `@autoresearch-experimenter` per task only when artifacts and budgets are isolated.

## Exit

Route to [01-intake.md](01-intake.md) for `active_task_id` (task-scoped state under `tasks/{id}/state.json`).
