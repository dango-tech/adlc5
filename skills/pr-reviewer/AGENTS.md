# PR Review (ADLC5) — contributor guide

ADLC5-native PR skill (`@pr-reviewer`). Orchestration lives in `SKILL.md` and `phases/`; repeatable work is in repo-root `scripts/pr-reviewer-*.sh`.

**Legacy @pr3** (Bitbucket) is a separate skill — typically `~/.cursor/skills/pr3` — not replaced by this directory.

## Layout

```
skills/pr-reviewer/
  SKILL.md
  phases/
  guides/github.md
  templates/
scripts/
  pr-reviewer-detect.sh
  pr-reviewer-compose-body.sh
  pr-reviewer-open.sh
  pr-reviewer-gh.sh
  pr-reviewer-check-merge.sh
```

## Testing

```bash
./scripts/tests/run-all.sh
./scripts/pr-reviewer-detect.sh --workspace .
```
