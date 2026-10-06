---
name: pr-reviewer-resolve
description: PR Review Phase 04 — Detect and resolve merge conflicts.
---

# Phase 04 — Resolve

## Purpose

Detect whether the feature branch merges cleanly into the base branch and guide conflict resolution.

## Steps

1. Check mergeability:

```bash
./scripts/pr-reviewer-check-merge.sh --workspace . --base {base_branch}
```

2. If `mergeable: true` — report ready to merge; stop.
3. If conflicts — update base and merge:

```bash
git fetch origin
git merge origin/{base_branch}
# resolve conflict markers in listed files
git add -A
git commit -m "merge: resolve conflicts with {base_branch}"
```

4. Re-run check:

```bash
./scripts/pr-reviewer-check-merge.sh --workspace .
```

5. Write `.adlc5/{feature}/pr-reviewer/resolve-status.md` with files touched and resolution notes.

6. **AskQuestion** before push if merge was complex or touched shared modules.

## Never do

- `git push --force` to shared branches without explicit user request
- Skip re-running tests after conflict resolution

## Exit criteria

- [ ] `pr-reviewer-check-merge.sh` exits 0
- [ ] User informed push/merge next step
