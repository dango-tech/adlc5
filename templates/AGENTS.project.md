# ADLC5 — Project agent guidance

This project uses **ADLC5** for spec → enterprise-grade code with TDD.

**Initialize:** run `scripts/init-workspace.sh` from your adlc5 clone (see `.adlc5/workspace.json`).

**Start a feature:** `@adlc5 for [feature-name]` (Cursor) or `/adlc5` (Claude Code).

**Lifecycle:** Specify → Plan → Tasks → Implement (`implement-1-build` … `implement-5-pr`).

**Production-ready ≠ story verified.** After stories are `verified`, run:

```bash
{adlc5_root}/scripts/check-gates.py --feature {feature} --workspace . --gate pr-ready
```

Governance copies: `.adlc5/governance/production-ready.md` · `.adlc5/governance/definition-of-done.md`

**Custom E2E / Docker gates:** define in `.adlc5/{feature}/policies.yaml` under `custom_gates` (consumer supplies the command, e.g. `pnpm test:e2e:frontend`).

**State:** `.adlc5/{feature}/state.json` (`schema_version: "3.0"`; canonical for ADLC5 4.x)

**Config:** `.adlc5/config.yaml` (project-local)

**Repository constitution (tracked):** read `AGENTS.md`, `.agents/architecture.yaml`,
`.agents/boundaries.yaml`, and `.agents/commands.yaml` before feature work. Changes to
architecture, boundaries, or canonical commands update these files deliberately in Git.

**Repository intelligence (generated):** `.agent-cache/` is gitignored and
regenerable. Refresh with `{adlc5_root}/scripts/adlc5 repo-index refresh --workspace .`;
read `repo-index.json` first, then only relevant symbol/module/dependency/test records.

**Project wiki (optional, team-shared):** `wiki/index.md` — brownfield KB; promote from `.adlc5/{feature}/memory/` only after `stage_status.implement: completed`. Init: `init-workspace.sh --with-project-wiki` · `@adlc5-project-wiki`

**Current information:** versions, protocol status, APIs, provider capabilities, security guidance, and current practices must be verified against official primary sources at task time. Record `last_verified`, status, and source URLs; stale or unverified load-bearing claims block delivery. See the ADLC5 clone's `core/guides/current-information.md`.

**Rules:** Global craftsmanship rules in `~/.cursor/rules/` (install once: `./scripts/install.sh --rules-only` from adlc5 clone).

## Invoke map

| Intent | Invoke |
|--------|--------|
| New feature | `@adlc5` |
| Specify only | `@adlc5-specify` |
| Engineering + design | `@adlc5-plan` |
| User stories + code specs | `@adlc5-tasks` |
| Profile-routed build → verify → integrate/QA → PR | `@adlc5-implement` |
| Autonomous route | `@adlc5` with autonomous mode |
| Project wiki | `@adlc5-project-wiki` |

Full index: [ADLC5 skill map](https://github.com/dango85/adlc5/blob/main/shared/docs/SKILL-MAP.md) or `AGENTS.md` in the installed ADLC5 clone.
