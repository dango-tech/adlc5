# Specify — Step 0: Git isolation

Run before requirements capture.

## AskQuestion

Options: `branch` | `worktree` | `current` | `skip` — map to `git.isolation`.

## Script

```bash
./scripts/git-orchestrate.sh --feature "{feature}" --action branch
```

## State updates

- Run `adlc5 pilot --feature "{feature}" --workspace "{workspace}"` for the mechanical Git check.
- On `halt`, use the reported bootstrap condition and next action. Resume the same feature after repair.
- On `advance`, pass the returned `transition_target` to `adlc5 transition`. The kernel checks the same Git binding before advancing.

## Gate

Git must be recorded (not `pending`) before `@discover` / `@prt`.
