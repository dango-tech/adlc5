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
- Advance using `adlc5 transition specify-1-discover --feature "{feature}"` after the step succeeds.

## Gate

Git must be recorded (not `pending`) before `@discover` / `@prt`.
