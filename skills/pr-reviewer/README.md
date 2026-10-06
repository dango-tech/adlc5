# PR Review (`@pr-reviewer`) — ADLC5

Pull request **Review, Respond, Resolve, and Open** — shipped inside [adlc5](https://github.com/dango85/adlc5) for the `@adlc5-implement` PR substep and autonomous `@adlc5` routing.

> **Not `@pr3`:** The legacy Bitbucket **PR3** skill (`@pr3`, `~/.cursor/skills/pr3`) is separate. Use **`@pr-reviewer`** for the ADLC5 lifecycle.

## Host support

| Host | Automation | Requirements |
|------|------------|--------------|
| **GitHub** | Full via `gh` | [GitHub CLI](https://cli.github.com/) + `gh auth login` |
| **Bitbucket** | Comments/MCP optional | `user-bitbucket-mcp-server` or manual UI |
| **GitLab / other** | Open manual + local git | Host UI for PR; scripts for merge check |

See [guides/github.md](guides/github.md) for GitHub workflows.

## Quick start (GitHub)

```bash
./scripts/pr-reviewer-detect.sh --workspace .
./scripts/pr-reviewer-compose-body.sh --feature my-feature --out /tmp/pr-body.md
./scripts/pr-reviewer-open.sh --feature my-feature --body-file /tmp/pr-body.md
```

In Cursor: `@pr-reviewer open my-feature` or `@pr-reviewer review my-feature`.

## Invoke map

| Action | Example |
|--------|---------|
| Open | `@pr-reviewer open {feature}` |
| Review | `@pr-reviewer review {feature}` |
| Respond | `@pr-reviewer respond {feature}` |
| Resolve | `@pr-reviewer resolve conflicts` |

## ADLC5 integration

- **Implement:** [implement-5-pr](../implement/phases/01-build-through-pr.md)
- **Autonomous route:** `@adlc5` calls `pr-reviewer-compose-body.sh` + `pr-reviewer-open.sh` at PR-ready
- **Git isolation:** branch from `.adlc5/{feature}/state.json` → `git.branch_name`
