# ADLC5 — Cross-platform guide

adlc5 skills use the [Agent Skills](https://agentskills.io/) standard (`skills/*/SKILL.md`). One repo, one install script, **seven host environments**.

## ADLC5 (recommended)

Install the SDD-first lifecycle (Specify → Plan → Tasks → Implement):

```bash
./scripts/install.sh --platform all
./scripts/verify-install.sh 
```

Docs: [docs/ADLC5.md](../../docs/ADLC5.md)

## Supported platforms

| Platform | Install target | Invoke | Context / rules |
|----------|----------------|--------|-----------------|
| **Cursor** | `~/.agents/skills`, `~/.cursor/rules` | `@adlc5` | `.mdc` rules, `AGENTS.md` |
| **Claude Code / CLI** | `~/.claude/skills` | `/adlc5` | [CLAUDE.md](../../CLAUDE.md), [shared/rules/portable/](../rules/portable) |
| **Codex / Codex CLI** | `~/.codex/skills`, `~/.agents/skills` | `skill({name:"adlc5"})` | [AGENTS.md](../../AGENTS.md); [`platform/codex-plugin/`](../../platform/codex-plugin/plugin.json) |
| **OpenCode** | `~/.config/opencode/skills`, `~/.agents/skills` | `skill({name:"adlc5"})` | [AGENTS.md](../../AGENTS.md) |
| **Gemini CLI** | `~/.gemini/skills` | load skill `adlc5` | [GEMINI.md](../../GEMINI.md), [templates/gemini-settings.json](../../templates/gemini-settings.json) |
| **Hermes Agent** | `~/.hermes/skills/adlc5` | `/skill adlc5` or `hermes -s adlc5` | [AGENTS.md](../../AGENTS.md), Hermes skill loader |
| **Antigravity** | `~/.gemini/config/plugins/adlc5-plugin` | load skill `adlc5` | [GEMINI.md](../../GEMINI.md), `AGENTS.md` |

## Install

```bash
git clone https://github.com/dango85/adlc5.git
cd adlc5
cp config.example.yaml config.yaml
chmod +x scripts/*.sh
./scripts/install.sh                 # all platforms (default)
./scripts/verify-install.sh
```

Single platform:

```bash
./scripts/install.sh --platform claude
./scripts/verify-install.sh --platform claude
```

Hermes Agent:

```bash
./scripts/install.sh --platform hermes
./scripts/verify-install.sh --platform hermes
```

Then start a fresh Hermes session or run `/reload-skills`, and load ADLC5 with `/skill adlc5`.

Dry run:

```bash
./scripts/install.sh --dry-run
```

Backup-replace: existing skill/rule entries are backed up under `install_backup_root` (default `~/.adlc5-install-backup/<timestamp>/`), replaced with symlinks, then the backup is removed after successful verify. On failure, the backup is kept for manual restore. `--keep-backup` skips deletion on success.

## Codex plugin (optional)

From the repo root:

```text
.cursor-plugin/plugin.json            →  skills skills/; mcpServers → .cursor-plugin/mcp.json; adlc5.kernel/mcp
.cursor-plugin/run-adlc5.sh|run-mcp.sh →  shims set ADLC5_ROOT → scripts/adlc5|adlc5-mcp.py
platform/codex-plugin/plugin.json  →  metadata + adlc5.kernel/mcp (skills via install.sh)
Runtime kernel                        →  $ADLC5_ROOT/scripts/adlc5 (install.sh prints ADLC5_ROOT)
```

**Cursor plugin load:** see [`.cursor-plugin/README.md`](../../.cursor-plugin/README.md). **Classic:** `./scripts/install.sh --platform <host>` (unchanged symlink matrix).

Install via Codex plugin UI or point your Codex config at `platform/codex-plugin/` only if `./skills/` is populated. Prefer `./scripts/install.sh --platform codex` for skills. Enable multi-agent for Delivery parallel implementation:

```toml
# ~/.codex/config.toml
[features]
multi_agent = true
```

## Consumer projects

`install.sh` runs from the **adlc5 distribution clone** and writes to user-global paths. `init-workspace.sh` runs from your **app repo** and links skills locally. Never set install targets to the clone’s own `skills/` folder.

Run `install.sh` once per machine, `init-workspace.sh` once per repository (in a linked git worktree it reuses the repository's shared `.adlc5` artifacts instead of duplicating them), and `init-feature.sh` once per feature. See [INSTALL.md — the three install layers](INSTALL.md#the-three-install-layers).

1. **Global rules (once):** `cd adlc5 && ./scripts/install.sh --rules-only`
2. **Initialize project:** `/path/to/adlc5/scripts/init-workspace.sh --project .`
3. Run lifecycle in that repo; state lives at `.adlc5/{feature}/`
4. Feature names (e.g. `visual-qa-tools`) are **your** kebab-case labels — folders under `.adlc5/`, not framework components
5. For Gemini CLI, add `.gemini/settings.json` from [templates/gemini-settings.json](../../templates/gemini-settings.json)

## Feature tiers

| Tier | What | All platforms? |
|------|------|----------------|
| **1** | Skills, knowledge base, `.adlc5/` state | Yes |
| **2** | Structured Q&A, subagents, invoke syntax | Adapters — [platform-tooling.md](../../core/guides/platform-tooling.md) |
| **3** | Cursor hooks, `.mdc` rules | Cursor only; portable rules in `shared/rules/portable/` |

## Structured user choices

| Host | Mechanism |
|------|-----------|
| Cursor | `AskQuestion` tool |
| Others | Native UI if available; else numbered options with same option ids |

See [askquestion-convention.md](../../core/guides/askquestion-convention.md).

## Portable rules

```bash
./scripts/sync-portable-rules.sh   # regenerates shared/rules/portable/*.md from .cursor/rules
```

Use in Claude/Gemini when `.mdc` is not supported.

## Smoke test checklist

- [ ] `./scripts/verify-install.sh` passes
- [ ] `./scripts/install.sh --print-version` matches `core/VERSION`
- [ ] `./scripts/resolve-model.sh --platform cursor --tier balanced` returns JSON
- [ ] Cursor: `@adlc5 for test-feature`
- [ ] Claude: `/adlc5` loads orchestrator skill
- [ ] Codex: `adlc5` appears in skill list
- [ ] OpenCode: `skill({name:"adlc5"})` works
- [ ] Gemini: skill `adlc5` discoverable (enable experimental skills if needed)
- [ ] Hermes: `/reload-skills`, then `/skill adlc5` loads the orchestrator
- [ ] Antigravity: skill under plugin or legacy antigravity skills path

## Updating

Agents: [INSTALL.md](INSTALL.md) § Agent self-update → `./scripts/update-adlc5.sh --self` | `--global`

## Troubleshooting

| Issue | Action |
|-------|--------|
| Skill not found | Re-run `./scripts/install.sh --platform <name>` |
| OpenCode name error | Skill folder name must match `name` in frontmatter (lowercase, hyphens) |
| Codex no parallel stories | Set `multi_agent = true` in config.toml |
| Gemini no skills | Enable `experimental.skills` in settings |
| Rules not applied outside Cursor | Use `shared/rules/portable/` or `CLAUDE.md` / `GEMINI.md` |
