# Installing adlc5

Agent Skills, rules, hooks (Cursor), knowledge base, and lifecycle scripts. Hosts: Cursor, Claude, Codex, OpenCode, Gemini, Hermes Agent, Antigravity — [CROSS-PLATFORM.md](CROSS-PLATFORM.md).

## Prerequisites

Git · Bash · one supported AI host · Python 3 (optional, for hooks)

## Quick start

```bash
git clone https://github.com/dango85/adlc5.git && cd adlc5
cp config.example.yaml config.yaml
./scripts/install.sh --platform cursor
./scripts/verify-install.sh 
```

**Consumer app repo:**

```bash
/path/to/adlc5/scripts/install.sh --rules-only                    # once per machine
/path/to/adlc5/scripts/init-workspace.sh --project . 
/path/to/adlc5/scripts/init-feature.sh --feature my-feature --interaction hitl
```

Invoke: `@adlc5 for my-feature`

## Config (`config.yaml`)

| Key | Purpose |
|-----|---------|
| `*_skills_target` / `rules_install_target` | Global install paths per host |
| `model_routing` | `strategy`, `execution_policy` (`inherit` \| `explicit`) |
| `platform_profiles` | Per-host tier → model IDs + spawn hints — [model-matrix.md](../../core/guides/model-matrix.md) |
| `model_profiles` | Flat fallback when platform unknown (backward compatible) |
| `council_models` | Discover council agent models (optional) |

Do **not** point install targets at this clone's `skills/` — `install.sh` refuses self-symlinks.

**Cleanup:** `install.sh` runs `cleanup-stale-skills.sh` before/after linking (skills + Cursor rules + aged backups by default; `--keep-backup` keeps this run’s backup and skips aged backup prune). Manual:

```bash
./scripts/cleanup-stale-skills.sh --prune-stale-skills --prune-stale-rules --platform all
./scripts/cleanup-stale-skills.sh --prune-backups --keep-backup-days 7
# Project-local skills (also run by init-workspace.sh):
./scripts/cleanup-stale-skills.sh --skills-target .agents/skills --prune-stale-skills
```

**Feature trees:** never deleted by install. Safe cleanup (dry-run archive by default; `--delete` for permanent remove):

```bash
./scripts/cleanup-features.sh --workspace . --status complete --older-than 90 --dry-run
./scripts/cleanup-features.sh --workspace . --status complete --older-than 90 --archive
./scripts/adlc5 cleanup-features --workspace . --status abandoned --older-than 30 --delete
# Opt-in on update (dry-run archive preview unless --prune-features-delete):
./scripts/update-adlc5.sh --self --prune-features --prune-features-older-than 90
```

**Model/token usage:** skills/agents record best-effort usage per stage via `./scripts/adlc5 usage record` (model id, platform, tier, input/output/thinking/cache tokens — see [ADLC5-kernel.md](../../docs/ADLC5-kernel.md)). The ledger lives at `.adlc5/{feature}/memory/usage-ledger.jsonl` and moves with the feature tree on archive; `--archive` embeds a Usage section in `FEATURE.md` and writes `usage-summary.json` next to it.

**Official Cursor usage reconciliation:** keep the Admin API key outside the
repository in `~/.adlc5/cursor-usage.env`, install workspace hooks with
`--with-hooks`, and enable the hourly collector:

```bash
./scripts/install-cursor-usage.sh
# Fill CURSOR_ADMIN_API_KEY and CURSOR_USAGE_EMAIL, then:
./scripts/install-cursor-usage.sh --enable
```

See [Cursor token usage collection](../../docs/cursor-usage.md).

## The three install layers

ADLC5 installs at three different scopes. Knowing which layer owns an artifact answers "why is this file here, and do I need one per repo/worktree?"

| Layer | Installed by | Scope | Contents |
|-------|--------------|-------|----------|
| 1. Machine-global | `install.sh` | Once per machine | Skills and rules **symlinked** out of this adlc5 clone into agent homes (`~/.agents/skills`, `~/.claude/skills`, `~/.codex/skills`, `~/.config/opencode/skills`, `~/.gemini/skills`, `~/.hermes/skills/adlc5`, `~/.cursor/rules`). Nothing is copied — every project, worktree, and agent host reads the same clone. |
| 2. Repository-local | `init-workspace.sh --project .` | Once per repository | `.adlc5/workspace.json`, `.adlc5/config.yaml`, `.adlc5/governance/`, `.adlc5/policies.yaml.example`, `AGENTS.md`, `.agents/`, `.agent-cache/`. Static for the repo. |
| 3. Per-feature | `init-feature.sh` / `@adlc5` | Once per feature | `.adlc5/{feature}/` — `state.json`, design docs, code specs, memory, usage ledger. |

### Why worktrees used to look like duplicate installs

`.adlc5/` is gitignored, and git never shares untracked files between worktrees — each linked worktree starts with an empty `.adlc5/`. Re-running `init-workspace.sh` there previously re-copied the whole layer-2 scaffold, so a repo with three worktrees carried three independent copies of files that are identical by definition.

`init-workspace.sh` is now worktree-aware. In a **linked** worktree it materializes the static layer-2 artifacts once at `<git-common-dir>/adlc5-shared/` — the same directory from every worktree, since `git rev-parse --git-common-dir` resolves to the one real `.git` — and symlinks the worktree's `.adlc5/config.yaml`, `.adlc5/governance/`, and `.adlc5/policies.yaml.example` at it. The shared store lives under the common `.git` dir rather than inside the first worktree, so it survives that worktree being removed. Existing real files are never converted, the main worktree keeps ordinary files, and `--no-shared-worktree` opts out.

**Layer 3 stays worktree-local on purpose.** Parallel worktrees exist to run different features; sharing `.adlc5/{feature}/` between them would merge unrelated lifecycle state. If two worktrees do end up with the same feature name, `init-feature.sh` warns and names the other worktree rather than merging silently.

`.agents/skills/*` remains a per-worktree symlink farm. Those links point straight at the adlc5 clone's `skills/`, so they resolve identically everywhere and hold no content — `init-workspace.sh` now says so explicitly instead of leaving it to be reverse-engineered.

## What `init-workspace.sh` creates

| Path | Purpose |
|------|---------|
| `.adlc5/workspace.json` | ADLC5-enabled project; records `adlc5_root` |
| `.adlc5/config.yaml` | Project `model_profiles`, HITL defaults |
| `.adlc5/governance/` | DoD, production-ready, verifier rules (symlinked to the repo's shared store in a linked worktree) |
| `.agents/` | Tracked constitution (`architecture.yaml`, `boundaries.yaml`, `commands.yaml`, `schemas/`) plus `skills/` symlinks |
| `AGENTS.md` | Agent guidance (if missing) |
| `.agent-cache/` | Generated repository intelligence (gitignored) |
| `.github/PULL_REQUEST_TEMPLATE.md` | Only with `--with-pr-template`, and only if the project has none |

**PR body template:** `@pr-reviewer` mirrors a repo's own PR template (`.github/pull_request_template.md` et al.) when opening a PR, populating it from the diff + ADLC5 facts and closing with an attribution trailer — [guides/pr-body-template.md](../../skills/pr-reviewer/guides/pr-body-template.md). No template? `init-workspace.sh --with-pr-template` copies ADLC5's starter ([templates/github/PULL_REQUEST_TEMPLATE.md](../../templates/github/PULL_REQUEST_TEMPLATE.md)) to `.github/PULL_REQUEST_TEMPLATE.md`; without the flag, init still prints a one-line suggestion when none is detected. Never overwrites an existing template.

Production-ready gate: `scripts/check-gates.py --gate pr-ready` (or `./scripts/adlc5 gate --feature NAME --gate pr-ready`)

**Kernel façade (4.x):** `./scripts/adlc5 --help` — [ADLC5-kernel.md](../../docs/ADLC5-kernel.md)

**MCP (optional):** `python3 ./scripts/adlc5-mcp.py` (stdio; `--smoke`). Plugin shims: `./.cursor-plugin/run-mcp.sh`. See [`.cursor-plugin/README.md`](../../.cursor-plugin/README.md). Also enable **Context7** (and wiki/Obsidian if you use them) so agents get current library/API docs — the in-repo KB stays timeless craftsmanship ([README](../../README.md#knowledge-base-vs-live-docs-mcp)).

**Agent Plugin vs classic install:** load the repo via [`.cursor-plugin/plugin.json`](../../.cursor-plugin/plugin.json) **or** keep using `./scripts/install.sh` for host skill/rule symlinks. Both need the distribution clone as `ADLC5_ROOT` for kernel/MCP.

## Install modes

| Mode | Command |
|------|---------|
| Project skills (recommended) | `init-workspace.sh --project . ` |
| Global skills only | `install.sh --skills-only ` |
| Global rules only | `install.sh --rules-only` |

Use project-local **or** global skills, not both, unless intentional.

## Verify

```bash
./scripts/verify-install.sh 
```

## Optional

**Hooks:** `init-workspace.sh --with-hooks` (secret scan, scope guard, test hint). Scope guard logs all preToolUse events; when `ADLC5_SCOPE_GUARD` or `policies.yaml` `scope_guard` is set, it **warns** on out-of-scope Write/StrReplace/Delete (default) or **denies** when mode/`ADLC5_SCOPE_GUARD` is `enforce`. Inactive without that metadata.

**Brownfield / large repo:** wiki bootstrap is **automatic** on `@adlc5` feature init (`profile-repo.py` + `ensure-wiki.sh`). Optional manual: [project-wiki.md](project-wiki.md)

**Repository context (all repos):** `init-workspace.sh` and `init-feature.sh` create
missing tracked `.agents/` constitution files and refresh `.agent-cache/`. Manual:
`./scripts/adlc5 repo-spec init|reconcile|validate` and `./scripts/adlc5 repo-index build|refresh|check`.

For an existing (brownfield) repo, run `init-workspace.sh`, then
`./scripts/adlc5 repo-spec reconcile --workspace .`. Keep `.agents/skills/` and any
other pre-existing `.agents/` files. If a leftover `.agent/` constitution exists,
reconcile copies missing yaml/schema into `.agents/` without overwriting. Review
drafts, validate, commit `.agents/` and `docs/adr/`, then delete only the leftover
constitution files under `.agent/` (leave `.agent/skills/` if Antigravity uses it).
For a new (greenfield) repo, run the same initialization before the first feature,
fill in architecture/boundaries/commands, and keep those tracked files current.
Do not commit `.agent-cache/`. Before planning a feature, run `repo-index check`
and refresh if it reports a stale or missing cache.
See [repository-context.md](../../core/guides/repository-context.md).

**Greenfield scaffold:** [scaffold-registry.md](../../core/guides/scaffold-registry.md)

**Council agents:** `install-council-agents.sh --target .cursor/agents` (also run by `init-workspace.sh`)

**CI security scan:** copy [templates/github-workflows/security-scan.yml](../../templates/github-workflows/security-scan.yml) to your app repo's `.github/workflows/` — semgrep + gitleaks + bandit on Linux and macOS runners. On macOS headless runners, `scripts/macos-security-fix.sh` fixes keychain/Gatekeeper failures (exit code 45) before scanning; the workflow applies the same fixes inline.

**Hermes Agent:** after `install.sh --platform hermes`, start a fresh session or run `/reload-skills`, then `/skill adlc5` — see [CROSS-PLATFORM.md](CROSS-PLATFORM.md).

## Updating

```bash
cd /path/to/adlc5 && git pull
./scripts/install.sh --rules-only
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app --force
```

Prefer the agent-friendly script below when an agent is performing the update.

## Agent self-update

When the user says any of the following, **do not invent steps** — run the mapped command from the adlc5 clone (or via `ADLC5_ROOT` / `.adlc5/config.yaml` → `adlc5_root`):

| User says | Exact command |
|-----------|----------------|
| "update adlc5 for yourself" / "update adlc5 for yourself to latest version" | `./scripts/update-adlc5.sh --self` (or `--platform <host>` when known) |
| "update adlc5 globally" | `./scripts/update-adlc5.sh --global` (same as `--platform all`) |

```bash
# Current host only (detects Cursor/Claude/Codex/… via env heuristics)
./scripts/update-adlc5.sh --self

# All install targets
./scripts/update-adlc5.sh --global

# Dry-run (no git pull mutations beyond printed plan; install --dry-run)
./scripts/update-adlc5.sh --self --dry-run

# Print version only
./scripts/install.sh --print-version
./scripts/verify-install.sh --print-version
```

The script: locates the adlc5 clone → prints `core/VERSION` → `git fetch` + `git pull --ff-only` → `./scripts/install.sh --platform …` → prints version again.

Semver source of truth: **`core/VERSION`**.

### Cleaning old / stale installs

`install.sh` runs `cleanup-stale-skills.sh` before and after linking. That removes:

- Retired skill names (forge-era `adlc5-forge-*`, `adlc5-engineer`, …)
- Broken symlinks into old ADLC5 clones
- Symlinks whose targets still point at legacy **`v1/skills`** or **`v2/skills`** paths
- Retired **ADLC5-owned** rule symlinks under `~/.cursor/rules` (never deletes user-authored plain rule files)
- Install backup dirs older than 7 days (default; skip with `install.sh --keep-backup`)

`init-workspace.sh` also prunes project-local `.agents/skills`.

```bash
./scripts/cleanup-stale-skills.sh --platform all --prune-stale-skills --prune-stale-rules
./scripts/cleanup-stale-skills.sh --prune-backups --keep-backup-days 7
./scripts/verify-install.sh
```

### Cleaning aged feature folders

`.adlc5/{feature}/` trees are **not** removed by install/update. Default action is **archive** to `.adlc5/_archive/{feature}-YYYYMMDD` (dry-run first). Successful `--archive` also writes an OKF v0.2 Feature summary (`FEATURE.md` + `_archive/index.md`; mirrors to `wiki/concepts/feature-{name}.md` when `wiki/` exists) plus, when any usage was recorded during the lifecycle, a `usage-summary.json` and a Usage section inside `FEATURE.md` (model IDs, token counts by type — input/output/thinking/cache — per model and per stage). Use `--delete` only for permanent remove (delete does not write a summary):

```bash
./scripts/cleanup-features.sh --workspace /path/to/app --status complete --older-than 90
./scripts/cleanup-features.sh --workspace /path/to/app --status complete --older-than 90 --archive
./scripts/cleanup-features.sh --workspace /path/to/app --status abandoned --older-than 14 --delete
./scripts/adlc5 feature summarize --feature-dir .adlc5/_archive/my-feature-20260809 --workspace .
./scripts/adlc5 usage summary --feature-dir .adlc5/_archive/my-feature-20260809 --format markdown
```

`complete` = all stage_status values completed/waived. `abandoned` = `lifecycle_status: abandoned` in state.json or an `ABANDONED` marker file.

If `update-adlc5.sh` warns about a **legacy `v2/` layout**, the clone is pre–path-lift: `git pull` onto 4.x (or re-clone), then install again so host skill dirs point at root `skills/`.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Skill not found | Re-run install; check `config.yaml` targets |
| Rules not applied | Check `~/.cursor/rules/` symlinks; restart Cursor |
| verify-install fails | Read FAIL lines; ensure targets exist and are writable |
| Hermes doesn't list adlc5 | `/reload-skills` or restart session; check `~/.hermes/skills/adlc5` symlink |
| Security tools fail on macOS CI (exit 45) | Run `scripts/macos-security-fix.sh` before scanning |
| Per-host issues | [CROSS-PLATFORM.md](CROSS-PLATFORM.md) troubleshooting table |

## See also

| Doc | Contents |
|-----|----------|
| [playbook.md](playbook.md) | Stages, craftsmanship, knowledge base |
| [SKILL-MAP.md](SKILL-MAP.md) | Invoke index |
| [docs/ADLC5.md](../../docs/ADLC5.md) | Lifecycle reference |
