# ADLC5 — Platform tooling adapters

**Mandatory reference** for all `@adlc5*` skills when the host is not Cursor. Skills and state (`.adlc5/`) are platform-agnostic; **tools and invoke syntax** differ.

See also: [askquestion-convention.md](askquestion-convention.md) (structured user choices).

## Invoke syntax

| Intent | Cursor | Claude Code / CLI | Codex / Codex CLI | OpenCode | Gemini CLI | Hermes Agent | Antigravity |
|--------|--------|-------------------|-------------------|----------|------------|--------------|-------------|
| Lifecycle orchestrator | `@adlc5` | `/adlc5` or load skill `adlc5` | `skill({name:"adlc5"})` | `skill({name:"adlc5"})` | load skill `adlc5` | `/skill adlc5` or `hermes -s adlc5` | load skill `adlc5` |
| Specify | `@adlc5-specify` | `/adlc5-specify` | `skill({name:"adlc5-specify"})` | same | same | `/skill adlc5-specify` | same |
| Plan | `@adlc5-plan` | `/adlc5-plan` | `skill({name:"adlc5-plan"})` | same | same | `/skill adlc5-plan` | same |
| Craftsmanship | `@clean-architecture-review` | `/clean-architecture-review` | `skill({name:"clean-architecture-review"})` | same | same | `/skill clean-architecture-review` | same |

**Auto-invoke:** On every platform, the agent loads skills by matching the skill `description` in frontmatter. Users can always invoke explicitly with the platform’s slash or skill tool.

## Structured user choices

| Platform | Preferred | Fallback |
|----------|-----------|----------|
| **Cursor** | `AskQuestion` tool | — |
| **Claude Code** | `AskUserQuestion` (if available) | Numbered options in chat; wait for reply |
| **Codex** | `request_user_input` / approval UI | Numbered options in chat |
| **OpenCode** | Permission `ask` on skill load | Numbered options in chat |
| **Gemini / Antigravity** | Built-in choice UI when present | Numbered options in chat |
| **Hermes Agent** | Numbered options in chat; wait for reply | — |

Always map the user’s answer to the same `option.id` values documented in [askquestion-convention.md](askquestion-convention.md) before updating `state.json`.

## Parallel subagents

| Cursor | Codex | Claude Code | Others (OpenCode, Gemini, Hermes, Antigravity) |
|--------|-------|-------------|------------------------------------------------|
| `Task` tool + `subagent_type: "build-implementer"` | `spawn_agent` with `multi_agent = true` in `~/.codex/config.toml` | `Task` / subagent with skill preload | Run stories **sequentially** in one session, or manual parallel sessions |

### Codex: build-implementer

1. Read [skills/build-implementer/SKILL.md](../../skills/build-implementer/SKILL.md).
2. Fill story context from canonical `tasks.stories[]` + `tasks/code-spec/{story-id}.md`.
3. `spawn_agent(agent_type="worker", message="Your task is… <agent-instructions>…</agent-instructions>")`.
4. Max 4 parallel workers when `policies.yaml` `defaults.execution_mode: parallel` (same as Cursor).

### Codex: discover LLM Council

Map `discover-council-claude`, `discover-council-gpt`, `discover-council-gemini` to three parallel `spawn_agent` calls with identical briefs (see [discover/phases/01-exploration.md](../../skills/discover/phases/01-exploration.md)).

### Claude Code: build-implementer

Use `Task` with subagent or `context: fork` on skill if configured; otherwise spawn subagent with implementer SKILL.md as system instructions.

## Rules and hooks

| Asset | Cursor | Other platforms |
|-------|--------|-----------------|
| Rules R0–R5 | `.cursor/rules/*.mdc` | [rules/portable/](../../shared/rules/portable/) or `CLAUDE.md` / `GEMINI.md` |
| Hooks H1–H3 | `.cursor/hooks.json` | **Not ported** — run secret scan / tests manually |
| AGENTS.md | Consumer projects | All platforms — set as context file where supported |

## Install paths (user-global)

After `./scripts/install.sh`, skills are symlinked under:

| Platform | Path |
|----------|------|
| Cursor / Codex (agents) | `~/.agents/skills/` |
| Claude | `~/.claude/skills/` |
| Codex (native) | `~/.codex/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Hermes Agent | `~/.hermes/skills/adlc5/` (path includes the skill root; `hermes_skills_target` in `config.yaml`) |
| Antigravity | `~/.gemini/config/plugins/adlc5-plugin/skills/` (or legacy `~/.gemini/antigravity/skills/`) |

See [docs/CROSS-PLATFORM.md](../../shared/docs/CROSS-PLATFORM.md).

## Detection

At skill start, infer platform from available tools:

- `AskQuestion` → Cursor-style Q&A form
- `skill(` in tool list → OpenCode
- `spawn_agent` → Codex multi-agent
- `/adlc5` slash commands → Claude Code
- `/skill` loader or `hermes` CLI in environment → Hermes Agent (no AskQuestion tool; use numbered options)

Do not assume Cursor-only tools exist; use fallbacks from this guide.

## Model selection

**Authoritative matrix:** [model-matrix.md](model-matrix.md)

**Resolver:** `./scripts/resolve-model.sh --platform <host> --tier <tier>`

**Config:** per-host structured tiers configured with `adlc5 setup models` — [config.example.yaml](../../config.example.yaml)

**Headless Codex runner (experimental):** configure model tiers with `./scripts/adlc5 setup models`, then start `./scripts/adlc5 run --feature NAME --host codex --workspace PATH` from a terminal. Workers use Codex CLI in `workspace-write` sandbox mode. The runner records each attempt and usage under `.adlc5/NAME/pilot/`; return code `10` means it is waiting for an answer, which can be recorded with `./scripts/adlc5 answer QUESTION_ID --text '...' --workspace PATH`. The benchmark gate in [headless-runner.md](../../docs/plans/headless-runner.md) remains open; this path is not yet qualified for cost or quality improvements.

| Tier | When | Host action |
|------|------|-------------|
| **reasoning** | Design, code spec, verify, `@qa`, Discover council | Select highest-capability model in picker |
| **balanced** | `@adlc5`, stories, integration, PR review | Default strong model |
| **execution** | `@build-implementer`, `@adlc5-tdd` (alias: `implementation`) | Select the configured execution tier |
| **fast** | Deprecated alias for execution | Resolves to execution with a notice |

| Platform | Apply tier |
|----------|------------|
| **Cursor** | [templates/cursor-models.md](../../templates/cursor-models.md) |
| **Claude Code** | [templates/claude-models.md](../../templates/claude-models.md) |
| **Codex** | [templates/codex-models.md](../../templates/codex-models.md) |
| **OpenCode** | [templates/opencode-models.md](../../templates/opencode-models.md) |
| **Gemini / Antigravity** | [templates/gemini-models.md](../../templates/gemini-models.md) |
| **Hermes Agent** | [templates/hermes-models.md](../../templates/hermes-models.md) |

On first skill invoke, show the tier notice and its configured source. Legacy `model_profiles` and `execution_policy` settings are ignored with a migration notice.

## Working memory

**Authoritative guide:** [working-memory.md](working-memory.md)

Feature context lives in `.adlc5/{feature}/memory/` (workspace-only). All platforms: read `INDEX.md` before loading full artifacts. Subagents use `context-packs/` when present.

## ADLC5 (four-stage SDD)

Install: `./scripts/install.sh`

| Intent | Invoke |
|--------|--------|
| Orchestrator + autopilot | `@adlc5` |
| Specify | `@adlc5-specify` |
| Plan | `@adlc5-plan` |
| Tasks | `@adlc5-tasks` |
| Implement | `@adlc5-implement` |

**State:** unified `.adlc5/{feature}/state.json` (`schema_version: "3.0"`).

**Scripts (all platforms):**

| Script | Purpose |
|--------|---------|
| `scripts/init-feature.sh` | Bootstrap feature |
| `scripts/pilot-autopilot.sh` | Autopilot iteration |
| `scripts/memory/budget-check.py` | Context budget |
**Hooks (portable):** `./scripts/hooks/boundary-check.sh` — run during Implement on any platform; Cursor also has `.cursor/hooks.json`.

Docs: [docs/ADLC5.md](../../docs/ADLC5.md)
