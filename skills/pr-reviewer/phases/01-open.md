---
name: pr-reviewer-open
description: PR Review Phase 01 — Open a pull request with ADLC5-composed body.
---

# Phase 01 — Open PR

## Purpose

Create a PR for the feature branch after the profile's Implement/pr-ready gates. Body includes QA clearance when required, story rollup, and telemetry summary.

## Prerequisites

- Feature branch exists (see [git-isolation.md](../../../core/guides/git-isolation.md))
- Gates passed: `deployment-clearance.md` recommended; pilot uses `check-gates.py --gate pr-ready`

## Steps

1. Read `.adlc5/{feature}/state.json` → `git.branch_name`; checkout that branch if needed.
2. Compose body — check `pr_template_path` from `pr-reviewer-detect.sh` first; mirror it
   when present, else use the default skeleton; always close with an attribution trailer
   ([guides/pr-body-template.md](../guides/pr-body-template.md)):

```bash
./scripts/pr-reviewer-compose-body.sh --feature "{feature}" --workspace . --out /tmp/pr-body-{feature}.md
```

3. **GitHub** — confirm `gh auth status`, then open:

```bash
./scripts/pr-reviewer-detect.sh --workspace .
./scripts/pr-reviewer-open.sh --feature "{feature}" --title "feat({feature}): ADLC5 delivery" \
  --body-file /tmp/pr-body-{feature}.md
```

4. Parse JSON stdout:
   - `status: opened` → record the actual `url` and `published: true` metadata under `implement.pr`
   - `status: exists` → PR already open for branch; record it under `implement.pr` and skip create
   - `status: manual` → non-GitHub or missing `gh`; show `body_file`, `branch`, `base`
   - `status: failed` → report error (`gh auth login` if unauthenticated)

5. **AskQuestion** only if title/base branch need confirmation (batch with draft yes/no if useful).

## Exit criteria

- [ ] PR URL recorded or user confirmed manual open
- [ ] Actual PR URL and `published: true` recorded in canonical state;
  local `pr-ready` completion remains a separate validated transition
