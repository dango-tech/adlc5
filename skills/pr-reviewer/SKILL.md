---
name: pr-reviewer
description: PR Review — Pull Request Review, Respond, Resolve, and Open. ADLC5-shippable PR workflow with first-class GitHub (gh CLI) and optional Bitbucket MCP. Use for @pr-reviewer, PR review, opening a feature PR at implement-5-pr, addressing review feedback, or checking merge conflicts.
author: ADLC5 Contributors
---

# PR Review — Pull Request (ADLC5)

## Intent

Shipped with **adlc5** for `implement-5-pr` and autonomous PR handoff. Covers:

| Action | Purpose |
|--------|---------|
| **Open** | Create a PR with body composed from ADLC5 artifacts |
| **Review** | Analyze the branch diff; companion to `@craftsmanship-code-review` (S1) |
| **Respond** | Triage and address review feedback |
| **Resolve** | Detect and fix merge conflicts locally |

**User invokes:** `@pr-reviewer for [feature]` or natural language (`open PR`, `review PR`, `resolve conflicts`).

**Scripts (mantra):** Orchestrator calls scripts; skills do not embed heavy shell.

| Script | Role |
|--------|------|
| `./scripts/pr-reviewer-detect.sh` | Provider, branch, `gh` availability (JSON) |
| `./scripts/pr-reviewer-compose-body.sh` | PR description from telemetry + QA + canonical state |
| `./scripts/pr-reviewer-open.sh` | `gh pr create` on GitHub; manual JSON for other hosts |
| `./scripts/pr-reviewer-gh.sh` | GitHub: status, diff, comments, post comment, CI checks |
| `./scripts/pr-reviewer-check-merge.sh` | Local merge-conflict probe |

**State:** `.adlc5/{feature}/pr-reviewer/state.json` (optional) + canonical lifecycle `state.json` → `git.branch_name`, `implement.pr`.

---

## Model recommendation

**Tier:** balanced — [model-matrix.md](../../core/guides/model-matrix.md).

---

## On invocation

1. **Feature name** — From user message or `.adlc5/{feature}/state.json`.
2. **Detect environment:**

```bash
./scripts/pr-reviewer-detect.sh --workspace .
```

3. **Parse action** (AskQuestion if ambiguous):

| Action | Triggers |
|--------|----------|
| `open` | open PR, create PR, pilot handoff, PR-ready |
| `review` | review PR, check PR, analyze diff |
| `respond` | address feedback, PR comments, respond |
| `resolve` | merge conflicts, conflicts with main |

4. **Read git context** from lifecycle state when present:

```json
"git": { "branch_name": "feat/my-feature", "worktree_path": "..." }
```

5. Delegate to the phase guide (below). Use **AskQuestion** for structured choices per [askquestion-convention.md](../../core/guides/askquestion-convention.md).

---

## Phase guides

| Action | Guide |
|--------|-------|
| Open | [phases/01-open.md](phases/01-open.md) |
| Review | [phases/02-review.md](phases/02-review.md) |
| Respond | [phases/03-respond.md](phases/03-respond.md) |
| Resolve | [phases/04-resolve.md](phases/04-resolve.md) |

---

## Provider support

### GitHub (first-class)

When `pr-reviewer-detect.sh` reports `provider: github` and `gh_authenticated: true`:

| Phase | Script |
|-------|--------|
| Open | `pr-reviewer-open.sh` → `gh pr create` (or `status: exists` if PR already open) |
| Review | `pr-reviewer-gh.sh --action status\|diff\|checks` |
| Respond | `pr-reviewer-gh.sh --action comments` → fix → `comment` |
| Resolve | `pr-reviewer-check-merge.sh` + `git merge` |

Full reference: [guides/github.md](guides/github.md).

```bash
gh auth login   # once per machine
./scripts/pr-reviewer-detect.sh --workspace .
```

Works with **GitHub.com** and **GitHub Enterprise** (`gh auth login --hostname`).

**PR body:** mirror the repo's own template when it has one, fall back to ADLC5's composed
skeleton otherwise, always close with an attribution trailer — [guides/pr-body-template.md](guides/pr-body-template.md).

### Other hosts

| Provider | Open | Review / respond | Resolve |
|----------|------|------------------|---------|
| **Bitbucket** | Manual UI or MCP | `user-bitbucket-mcp-server` when configured | `pr-reviewer-check-merge.sh` + git |
| **GitLab / generic** | Manual UI | Local `git diff` + pasted comments | `pr-reviewer-check-merge.sh` + git |

Legacy Bitbucket workflow files under `workflows/` are **not** used by ADLC5 orchestration.

---

## ADLC5 integration

| Caller | Behavior |
|--------|----------|
| `@adlc5-implement` | `implement-5-pr` — review + merge-ready |
| autonomous `@adlc5` | On `action: done` — run **Open** with composed body |
| `@craftsmanship-code-review` | Run **Review** analysis after or with S1 |

Update lifecycle state on completion:

```json
"implement": { "pr": { "status": "completed", "url": "..." } }
```

---

## Never do

- Force-push `main`/`master` without explicit user request
- Skip `pr-reviewer-detect.sh` before open/resolve
- Store tokens in repo files
- Replace S1 architecture/pattern reviews — PR Review is pipeline PR mechanics

## Always do

- Prefer feature branch from `state.json` / `git-isolation.md`
- Check `pr_template_path` first; mirror a repo template's headings, else compose via
  `pr-reviewer-compose-body.sh` — [guides/pr-body-template.md](guides/pr-body-template.md)
- Close the PR body with an attribution trailer for agent-authored work
- Report PR URL and `pr-reviewer/state.json` path when done
