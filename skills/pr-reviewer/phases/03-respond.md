---
name: pr-reviewer-respond
description: PR Review Phase 03 — Address PR review feedback.
---

# Phase 03 — Respond

## Purpose

Triage review comments, fix code, and re-run gates before re-requesting review.

## Steps

1. Load PR context — URL from `state.json` `implement.pr.url` or user message.
2. Fetch comments:
   - **GitHub:** `./scripts/pr-reviewer-gh.sh --action comments --branch "{branch}"` → save JSON to `.adlc5/{feature}/pr-reviewer/comments.json`
   - **Bitbucket:** `user-bitbucket-mcp-server` → `get_pull_request_comments` when configured
   - **Otherwise:** user pastes comment list; store in `.adlc5/{feature}/pr-reviewer/comments.md`

3. Triage each comment (AskQuestion batch when >3 ambiguous items):

| Disposition | Action |
|-------------|--------|
| Fix now | Patch in feature branch |
| Defer | Log in `respond-log.md` with rationale |
| Won't fix | Reply with justification |

4. After fixes, run deterministic checks:

```bash
./scripts/run-tests.sh --feature "{feature}"
./scripts/run-lint.sh --feature "{feature}"
```

5. Commit with conventional message; push branch.
6. Reply on host:
   - **GitHub:** `./scripts/pr-reviewer-gh.sh --action comment --branch "{branch}" --body "..."`
   - **Bitbucket:** MCP or manual
7. Append `.adlc5/{feature}/pr-reviewer/respond-log.md` with triage table.

## Exit criteria

- [ ] All blocking comments addressed or explicitly deferred with user approval
- [ ] Tests/lint re-run pass or risks documented
