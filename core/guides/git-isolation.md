# ADLC5 — Git isolation (before Specify)

**Mandatory gate:** Git isolation must be **completed** or **explicitly skipped** before any Specify-stage requirements work (`@discover`, `@prt`, inline PRD import, or `spec-handoff.md`).

**Who runs this:** `@adlc5` on first invocation; `@adlc5-specify` phase [00-git-isolation.md](../../skills/specify/phases/00-git.md) when Specify is entered without a completed `git` block in state.

**User interaction:** [askquestion-convention.md](askquestion-convention.md) — use **AskQuestion** on Cursor.

---

## Preconditions

1. Run from the **consumer project** workspace (application repo), not the adlc5 install repo.
2. Detect git: `git rev-parse --is-inside-work-tree` (exit 0 = proceed; else offer **skip** only).
3. Record `git.repository_root` via `git rev-parse --show-toplevel`.

---

## Step 1 — Report context

Always tell the user:

- Current branch: `git branch --show-current`
- Default suggested branch: `feat/{feature-name}` (override via `config.yaml` → `git_branch_prefix`, default `feat`)
- Whether the workspace is already a linked worktree: `git rev-parse --git-dir` (if path contains `worktrees`, note it)

---

## Step 2 — AskQuestion (one call, up to 2 questions)

### Question 1 — `git_isolation`

| `id` | `label` |
|------|---------|
| `branch` | Create feature branch `feat/{feature}` and check it out here (recommended) |
| `worktree` | Add isolated worktree + new branch (work on feature in a separate directory) |
| `current` | Stay on current branch (`{current-branch}`) |
| `skip` | Skip git isolation (not a git repo, or I will manage branches myself) |

### Question 2 — `branch_name` (only when Q1 is `branch` or `worktree`)

| `id` | `label` |
|------|---------|
| `default` | Use `feat/{feature-name}` |
| `custom` | I will type a custom branch name in chat |

If `custom`, read the name from chat; validate with `git check-ref-format --branch "{name}"`.

---

## Step 3 — Execute choice

To execute the choice, run the repeatable git isolation script:

```bash
./scripts/git-isolation.sh --feature "{feature-name}" --action "{branch|worktree|current|skip}" [flags]
```

This script handles the heavy lifting, directory verification, worktree checkout, and `.gitignore` safety. It outputs the exact JSON state to merge into `state.json`.

### Manual Fallback Reference (if script is missing or fails)

```bash
git fetch origin 2>/dev/null || true
git checkout -b "{branch_name}"   # if branch exists: git checkout "{branch_name}"
```

If branch already exists locally, **AskQuestion**: checkout existing vs create new name.

If current branch is `main` or `master` and user chose `current`, warn and require explicit confirmation before proceeding.

### `worktree`

1. **Resolve worktree parent directory** (priority order):
   - `git_worktree_directory` from consumer `config.yaml` / `config.example.yaml` if set
   - Existing `.worktrees/` or `worktrees/` in repo root
   - **AskQuestion** if none: `.worktrees/` (project-local) vs path under `~/.adlc5-worktrees/{project-basename}/`

2. **Safety** (project-local only):

```bash
git check-ignore -q "{worktree_parent}" || {
  # Add to .gitignore, commit only if user approves via AskQuestion
}
```

3. **Create:**

```bash
mkdir -p "{worktree_parent}"
git worktree add "{worktree_parent}/{branch_name}" -b "{branch_name}"
```

4. Record `git.worktree_path` as the **absolute** path returned by `git worktree list`.

5. Tell the user to **open the worktree folder** in Cursor (or `cd` there) before Specify artifacts are written. Prefer creating `.adlc5/{feature}/` in the **worktree** when the user confirms they switched workspace.

6. A new worktree starts with an empty `.adlc5/` (it is gitignored, and git never shares untracked files between worktrees). Run `init-workspace.sh --project {worktree}` there: it symlinks the repo's shared `config.yaml`, `governance/`, and `policies.yaml.example` from `<git-common-dir>/adlc5-shared/` instead of duplicating them. Only `.adlc5/{feature}/` is genuinely worktree-local. See [INSTALL.md](../../shared/docs/INSTALL.md#the-three-install-layers).

### `current`

- Set `git.isolation` to `current`.
- If on `main`/`master`, **AskQuestion** confirm before marking complete.

### `skip`

- Set `git.isolation` to `skipped`, `git.status` to `waived`.
- Require user acknowledgment in Q&A (option label states they manage git).

---

## Step 4 — Update `state.json`

```json
"git": {
  "status": "completed|waived|failed|pending",
  "isolation": "branch|worktree|current|skipped",
  "branch_name": "feat/my-feature",
  "base_branch": "main",
  "worktree_path": null,
  "repository_root": "/abs/path/to/repo",
  "completed_at": "2026-05-20T12:00:00Z"
}
```

On failure, set `status: "failed"`, report error, do **not** start `@discover` / `@prt`.

---

## Hard gate (enforced)

| Blocked until `git.status` is `completed` or `waived` | Allowed after gate |
|------------------------------------------------------|-------------------|
| `@discover`, `@prt`, `@vision`, `@prd` for this feature | Git isolation step |
| Writing `spec-handoff.md`, PRT/Discover artifact paths in state | Initial `state.json` + `memory/` scaffold |
| Advancing `stage_status.specify` beyond setup | — |

**Resume:** If `git.status` is `pending`, run this guide before any Specify phase file.

---

## Integration and PR completion

Record `git.branch_name` in state so `@pr-reviewer` can identify the feature branch without re-asking.
