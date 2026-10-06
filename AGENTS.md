# adlc5 — Agent guidance

**Lifecycle:** Specify → Plan → Tasks → Implement — agent judgment + deterministic kernel — **`@adlc5 for [feature]`**

Install: `./scripts/install.sh` · Version: `core/VERSION` · Update: `./scripts/update-adlc5.sh --self` \| `--global` · Reference: [docs/ADLC5.md](docs/ADLC5.md)

## Essentials

| Topic | Location |
|-------|----------|
| Install / agent self-update | [shared/docs/INSTALL.md](shared/docs/INSTALL.md) |
| Playbook (stages, craftsmanship) | [shared/docs/playbook.md](shared/docs/playbook.md) |
| Skill invokes | [shared/docs/SKILL-MAP.md](shared/docs/SKILL-MAP.md) |
| Knowledge base (on demand) | [shared/docs/knowledge-base/](shared/docs/knowledge-base/README.md) — timeless craftsmanship; live libs/APIs → Context7 + other MCPs ([README](README.md#knowledge-base-vs-live-docs-mcp)) |
| Cross-platform | [shared/docs/CROSS-PLATFORM.md](shared/docs/CROSS-PLATFORM.md) |
| Model routing | [core/guides/model-matrix.md](core/guides/model-matrix.md) · `./scripts/resolve-model.sh` |
| Current information | [core/guides/current-information.md](core/guides/current-information.md) — verify volatile claims against official primary sources before shipping |
| Evidence-driven fat kernel (4.x) | [docs/ADLC5-kernel.md](docs/ADLC5-kernel.md) · `./scripts/adlc5` · MCP `./scripts/adlc5-mcp.py` · plugin [`.cursor-plugin/`](.cursor-plugin/) |

**Mantra:** Repeatable work → scripts; skills call scripts using the SDD.

## Invoke map

| Intent | Invoke |
|--------|--------|
| New feature (full lifecycle) | **`@adlc5`** |
| Single stage | `@adlc5-specify` · `@adlc5-plan` · `@adlc5-tasks` · `@adlc5-implement` |
| Reasoning guard (fifth pillar, cross-cutting) | `@adlc5-soul` |
| Requirements / discovery | `@discover` · `@prt` |
| Architecture review | `@clean-architecture-review` |
| Patterns | `@design-pattern-advisor` · `@pbe-select-patterns` |
| Algorithms (scale NFRs) | `@algorithm-advisor` |
| TDD build | `@build-implementer` · `@adlc5-tdd` |
| Verify story | `@assure-verifier` |
| Quality / security gate | `@qa` |
| PR workflow | `@pr-reviewer` · `@craftsmanship-code-review` |
| Pattern catalog (recurrence) | `@pbe-pattern-opportunity` → S8 → S7 |
| Project wiki | `@adlc5-project-wiki` |
| IaC / deployment (post-PR) | `@infra` · `@deploy` |
| Experimentation loops | `@autoresearch` |

Structured choices: **AskQuestion** — [askquestion-convention.md](core/guides/askquestion-convention.md)

## Workspace facts

- Feature names under `.adlc5/{feature}/` are **your** kebab-case labels.
- This repo is the **framework distribution** — run lifecycles in consumer app repos, not here (except `dogfood/`).
- Knowledge base in `shared/docs/knowledge-base/` is the sole in-repo book reference — no PDF paths in config.
- Hooks: `.cursor/hooks.json` — secret scan, scope guard (warn by default when scope metadata/`ADLC5_SCOPE_GUARD` is set; `enforce` denies out-of-scope writes), post-edit test hint.
- Production-ready = `check-gates.py --gate pr-ready` (or `./scripts/adlc5 gate`), not story `verified` alone.
- ADLC5 4.x = single tree at repo root (`core/`, `skills/`, `scripts/`, …); VERSION in `core/VERSION`. No dual-version docs or parallel version tree.
- Spine ops go through `./scripts/adlc5` (and thin MCP `./scripts/adlc5-mcp.py`); do not treat A2A as the SDLC kernel or invent a second gate/state engine.
- Project wiki is team-shared whole-repo memory; feature memory promotes only after `stage_status.implement: completed` with human-approved evidence.
- Install/update prunes stale ADLC5 **skill and rule symlinks** (legacy forge names, `v1/skills`, `v2/skills` targets, retired `.mdc` rule links under `~/.cursor/rules`) and aged install backups by default (`--keep-backup` opts out). Project-local `.agents/skills` is pruned on `init-workspace.sh`. Feature trees under `.adlc5/{feature}/` are **not** auto-moved or auto-deleted when a feature completes — use `./scripts/cleanup-features.sh` / `./scripts/adlc5 cleanup-features` (archive to `_archive/` by default; `--archive` writes OKF `FEATURE.md` + `_archive/index.md`; `--delete` for permanent remove) or `update-adlc5.sh --prune-features`.
- Model + token usage: record per-stage/per-call usage with `./scripts/adlc5 usage record --feature NAME --model-id ID [--input-tokens N --output-tokens N --thinking-tokens N --cache-creation-tokens N --cache-read-tokens N ...]` (best-effort, self-reported; unknown platform counters go in `--extra-json`). Ledger lives at `.adlc5/{feature}/memory/usage-ledger.jsonl` and rides along when `cleanup-features --archive` moves the feature tree; the archive step embeds a Usage section (tokens by type, by model, by stage) in `FEATURE.md` and writes `usage-summary.json`. `./scripts/adlc5 usage summary --feature NAME` is per-feature; `./scripts/adlc5 usage fleet --workspace .` rolls totals up across every feature in the workspace (active + `_archive/`, `--active-only` to exclude archived) with `by_model`/`by_stage`/`by_feature` breakdowns. Both `summary` and `fleet` also attach a self-reported `cost_usd` per bucket, priced from [`core/model-prices.yaml`](core/model-prices.yaml) (`last_verified` snapshot, not a live billing API); a `model_id` missing from that table reports `cost_usd: null` for its calls and is listed under `unpriced_models` rather than silently costing `$0`.
- Cost tiering: `.adlc5/{feature}/policies.yaml` may set `model_routing.execution_policy: explicit` to route `implement-1-build` subagents to the cheap execution tier for this feature regardless of the global `config.yaml` default (`inherit`); `templates/policies-tiny.yaml.example` and `templates/policies-standard.yaml.example` ship with it on, `templates/policies-high-risk.yaml.example` ships with `inherit`. See [core/guides/model-matrix.md](core/guides/model-matrix.md).
- Code specs (`tasks/code-spec/{story-id}.md`) carry a required YAML frontmatter block (`story_id`, `files_to_create`/`files_to_modify`, `tests[]`, `acceptance_criteria`, optional `signatures[]`) validated by `./scripts/tasks/spec-lint.py` — this backs the `tasks-2-code-spec-complete` gate, replacing a bare "directory has `.md` files" check. Skeleton: [templates/feature-docs/code-spec.md](templates/feature-docs/code-spec.md). `./scripts/verify-story.py --feature NAME --story-id ID` runs the mechanical half of story verification (file boundary, declared tests present + passing, lint clean, debug-noise scan, signature cross-check against `.agent-cache/symbols.json` when built) before `@assure-verifier` reasons about the rest; it feeds the `implement-2-verify` gate additively when a story has frontmatter, and is a no-op for features that don't.
