# PR Review (ADLC5) — GitHub (`gh` CLI)

First-class GitHub support for `@pr-reviewer`. Requires [GitHub CLI](https://cli.github.com/) authenticated in the consumer project workspace.

## Prerequisites

```bash
gh --version
gh auth login
gh auth status
```

Detect readiness:

```bash
./scripts/pr-reviewer-detect.sh --workspace .
# provider: github, has_gh: true, gh_authenticated: true, repo_slug: owner/repo
```

## Scripts

| Script | GitHub use |
|--------|------------|
| `pr-reviewer-detect.sh` | Provider, `repo_slug`, open `pr_number` for current branch |
| `pr-reviewer-compose-body.sh` | PR body (host-agnostic) |
| `pr-reviewer-open.sh` | `gh pr create`; returns `exists` if PR already open |
| `pr-reviewer-gh.sh` | `status`, `diff`, `comments`, `comment`, `checks` |
| `pr-reviewer-check-merge.sh` | Local merge probe (any host) |

## Actions by phase

### Open

```bash
./scripts/pr-reviewer-compose-body.sh --feature "{feature}" --out /tmp/pr-body.md
./scripts/pr-reviewer-open.sh --feature "{feature}" --body-file /tmp/pr-body.md
```

Record the actual `url` and `published: true` metadata from JSON in `.adlc5/{feature}/state.json` → `implement.pr`.

### Review

```bash
./scripts/pr-reviewer-gh.sh --action status --branch "{branch}"
./scripts/pr-reviewer-gh.sh --action diff --branch "{branch}"
./scripts/pr-reviewer-gh.sh --action checks --branch "{branch}"
```

Fallback when no PR exists yet: `git diff origin/{base}...HEAD`.

### Respond

```bash
./scripts/pr-reviewer-gh.sh --action comments --branch "{branch}"
# after fixes:
./scripts/pr-reviewer-gh.sh --action comment --branch "{branch}" --body "Addressed feedback in ..."
```

Parse `comments` JSON for review threads; triage in `.adlc5/{feature}/pr-reviewer/respond-log.md`.

### Resolve

```bash
./scripts/pr-reviewer-check-merge.sh --workspace . --base main
git fetch origin && git merge origin/main
```

## GitHub.com vs GitHub Enterprise

`gh` uses `GH_HOST` / `gh auth login --hostname` for Enterprise Server. `pr-reviewer-detect.sh` treats any `github.com` or `github:` remote as `provider: github`.

## Optional: GitHub MCP

When a GitHub MCP server is configured in Cursor, the orchestrator may use it instead of `gh` for the same operations — prefer **`pr-reviewer-gh.sh`** for deterministic JSON in autonomous `@adlc5` runs.
