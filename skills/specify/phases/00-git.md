# Specify — Step 0: Git isolation

Run before requirements capture.

## AskQuestion

Options: `branch` | `worktree` | `current` | `skip` — map to `git.isolation`.

## Script

```bash
./scripts/git-orchestrate.sh --feature "{feature}" --action branch
```

## State updates

- `git.isolation`, `git.branch_name`, `git.base_branch`, `git.worktree_path`
- `current_step`: `specify-1-discover` on success

## Gate

Git must be recorded (not `pending`) before `@discover` / `@prt`.
