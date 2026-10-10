# Changelog

## [Unreleased]

### Added

- **Supervised headless Codex runner:** `adlc5 run` drives the existing navigator with isolated Codex CLI workers, worktree isolation, attempt checkpoints, retry escalation, kill-switch and timeout supervision, kernel-ingested evidence, and per-attempt usage records. `adlc5 answer` resumes a pending human question; `adlc5 setup models` and `adlc5 config show` manage and inspect user-selected Codex tiers. MCP exposes run and answer operations.
- **Acceptance traceability:** code specs map each acceptance criterion to declared named checks; spec lint and story verification reject missing or stale mappings.

### Changed

- Model IDs are user-selected rather than shipped as defaults; repo configuration is shared in the Git common directory and machine paths stay in `workspace.json`.
- Benchmark results have not qualified the runner yet. M2 requires six runs for both the docs and real-code features; cross-host adapters and storage changes remain gated on that decision. See [the implementation record](docs/plans/headless-runner.md#8-milestones).

## [5.0.0] — Claude Code plugin and MCP/kernel path contracts

Major version: the MCP transport framing changes (standard newline-delimited stdio replaces `Content-Length` framing) and kernel subprocesses now inherit the caller's cwd. Lifecycle state schema stays 3.0; existing `.adlc5/` state is unaffected. Skill versions are synchronized to 5.0.0.

### Added

- **Claude Code plugin (local package):** `.claude-plugin/plugin.json`, `.mcp.json`, `hooks/claude.json` (SessionStart, UserPromptSubmit, PreToolUse, Stop), `bin/adlc5` / `bin/adlc5-run`, the shared `adlc5-setup` skill (`scripts/plugin-setup.sh`), and a deterministic archive builder `scripts/package-plugin.py` (tar.gz + zip, installed packages carry an immutable `.adlc5-package.json` marker). Claude hook wrappers resolve the current plugin runtime (`CLAUDE_PLUGIN_ROOT`) before any workspace binding. `init-workspace.sh` gains `--no-council-agents` and `--refresh-runtime` (`scripts/rebind-runtime.py` repairs only a stale `adlc5_root`). Tests: `scripts/tests/test-claude-plugin.py`.

- Added repository context initialization and deterministic local intelligence indexes for brownfield and greenfield workspaces (`.agents/` constitution and gitignored `.agent-cache/`), with CLI, MCP, installation, and lifecycle integration. `repo-spec init` writes constitution beside existing `.agents/skills/`; `repo-spec reconcile` copies useful leftover `.agent/` yaml/schema into `.agents/` without overwriting, then documents what to keep vs delete.
- **Cost-optimization pass** (lifecycle model/token spend, not a state-schema change): four levers, additive and off-by-default except where noted.
  - **Per-feature `execution_policy` override:** `.adlc5/{feature}/policies.yaml` may now set `model_routing.execution_policy: explicit`, which wins over the `config.yaml` global default for that feature only, routing `implement-1-build` subagents to the cheap execution tier. New template [`templates/policies-standard.yaml.example`](templates/policies-standard.yaml.example) fills the gap between tiny and high-risk; it and `templates/policies-tiny.yaml.example` ship with `explicit`, `templates/policies-high-risk.yaml.example` ships with `inherit` explicitly. `resolve-model.sh` output gains `execution_policy_source` (`"config"` | `"feature_policy"`).
  - **Machine-checkable code specs:** `tasks/code-spec/{story-id}.md` now carries a required YAML frontmatter block (`story_id`, `files_to_create`/`files_to_modify`, `tests[]`, `acceptance_criteria`, optional `signatures[]`), validated by new [`scripts/tasks/spec-lint.py`](scripts/tasks/spec-lint.py) (`./scripts/adlc5 spec-lint`). This backs the `tasks-2-code-spec-complete` gate, replacing the previous "directory has `.md` files" check. Skeleton: [`templates/feature-docs/code-spec.md`](templates/feature-docs/code-spec.md).
  - **Deterministic per-story verification:** new [`scripts/verify-story.py`](scripts/verify-story.py) (`./scripts/adlc5 verify-story`) mechanically checks file boundary (git-changed files vs. declared spec), declared tests present and passing, lint clean, no obvious debug leftovers, and best-effort signature cross-check against `.agent-cache/symbols.json` — before `@assure-verifier` reasons about what's actually left. Feeds `implement-2-verify` and `pr-ready` additively (a `deterministic_verify_{story-id}` check) only for stories whose code spec has frontmatter; a no-op for features without it.
  - **Priced usage ledger:** new [`core/model-prices.yaml`](core/model-prices.yaml) (a dated pricing snapshot, not a live billing API). `./scripts/adlc5 usage summary` / `usage fleet` now attach an estimated `cost_usd` per bucket (`by_model`/`by_stage`/`by_feature`/`totals`); a `model_id` missing from the table reports `cost_usd: null` and is listed under `unpriced_models` instead of silently costing `$0`.
  - New shared parser [`scripts/lib/simple_yaml.py`](scripts/lib/simple_yaml.py) (no PyYAML dependency) backs both the pricing table and code-spec frontmatter parsing.

### Changed

- `scripts/adlc5-mcp.py` now speaks standard newline-delimited MCP stdio (it previously used `Content-Length` framing, which standard clients do not send), validates tool arguments, keeps child processes off the protocol stream, resolves an explicit consumer workspace, and refuses workspaces inside an installed package.
- `scripts/adlc5` runs delegated scripts from the caller's cwd (was the framework root), so `--workspace .` and relative file arguments resolve against the consumer repository.
- The Claude engagement-gate hook no longer returns `permissionDecision: allow` in warn mode (it granted edits without the user's permission prompt); warn adds context only and `enforce` still denies.

- `tasks-2-code-spec-complete` (and therefore `tasks-complete`) now fails a code spec whose frontmatter is missing or malformed, not just an empty `tasks/code-spec/` directory. An in-flight feature with pre-existing code specs written before this change will need frontmatter added (`./scripts/tasks/spec-lint.py` reports exactly what each file is missing) before that gate passes again.

## [4.0.1] — Current information and A2UI correction

### Changed

- Added a mandatory current-information policy for volatile versions, APIs, protocols, provider capabilities, security guidance, and current recommendations. Specify/Plan must verify official primary sources and record `last_verified`, status, and source URLs.
- Updated the AI-agent orchestration guide to the current A2UI landscape: v0.9.1 is stable, v1.0 is a release candidate, and v1 removes protocol-level `theme`/`primaryColor` so branding remains renderer-owned.
- Synchronized the five core lifecycle skills plus cross-cutting SOUL with framework/plugin version 4.0.1; auxiliary skills retain independent component versions and persisted lifecycle state remains schema 3.0.
- Updated generated consumer `AGENTS.md`, model/interaction/memory/governance guides, templates, and auxiliary handoffs to the canonical Specify → Plan → Tasks → Implement lifecycle; retired commands remain only in explicit deprecation/history/legacy-alias references.
- Made Bash and Python state readers prefer valid schema-v3 `state.json`, with explicit delivery/forge fallbacks for older workspaces; canonical memory, coverage, retry, and PR-body paths now share that contract.
- Aligned PR-review instructions and generated bodies with `implement.pr`, including the required agent-attribution trailer, and verified links after governance files are copied into a consumer workspace.
- Removed the canonical `pr-ready` completion cycle: evidence is checked at `implement-5-pr`, then `stage_status.implement` may transition to `completed`.
- Hardened PR, deploy, verifier-waiver, and project-wiki approvals to reject agent-authored or missing human provenance; wiki promotion now validates completed schema-v3 Implement state before any mutation.
- Fixed autonomous terminal routing so `implement-5-pr` evaluates `pr-ready` and returns `done` instead of advancing to itself.
- Confined project-wiki promotion targets to `wiki/entities/` or `wiki/concepts/`, validated before the first write.
- Aligned production-ready guidance with profile routing: QA is mandatory when the selected profile enables `implement-4-qa`, not fabricated for profiles that explicitly skip it.
- Reject unknown wiki promotion actions and symlinked wiki roots that resolve outside the workspace/wiki boundary.
- Parse QA clearance from an exact authoritative status field with `BLOCKED` dominance, and validate canonical state against the full schema before preferring it over legacy fallback state.

Existing consumer `AGENTS.md` files are intentionally never overwritten by `init-workspace.sh`; merge the current-information rule from `templates/AGENTS.project.md` when upgrading an existing workspace.

## [4.0.0] — Evidence-driven work graph controls

### Breaking changes

- High-risk work now requires acceptance definitions to be locked before Implement and fresh-session/different-model verifier evidence before Verify and `pr-ready`.
- Evaluated runs qualify as successful only with passing profile quality gates, zero escaped defects, and finite non-negative usage correlated by `run_id` and `node_id`.
- Canonical schema-v3 `state.json` now takes precedence over stale legacy `delivery/state.json`. The persisted state schema remains `3.0`; this is a framework/workflow major release, not a state-format rewrite.

### Added

- Explicit tiny, standard, and high-risk routes with validated story dependency graphs and parallel file-ownership checks.
- Acceptance-manifest locking with file digests, command-definition checks, approved relocking, and a local Git ref for ordinary worktree-tamper detection.
- Node-level telemetry, usage, retry, finding, outcome, successful-spend, and failed-spend evaluation without a blended quality score.
- SOUL 4.0 keeps its five guards but makes them graph/evidence-aware: preserve consumer acceptance, select the minimum sufficient profile, honor dependency/file ownership, require independent verification, and optimize cost only after the quality floor.

### Migration

1. Re-run `./scripts/install.sh` (or the platform-specific update path) so skills, policies, and kernel scripts match 4.0.0.
2. For in-flight high-risk features, run `./scripts/adlc5 anchors lock --feature NAME` before Implement and record `implement.verification.independence` before Verify.
3. Keep `schema_version: "3.0"`; no state-version edit is required. Remove or ignore stale legacy `delivery/state.json` once canonical state is authoritative.
4. Treat `refs/adlc5/anchors/*` as local worktree-tamper references. They are not transferred by normal Git remotes and do not defend against a repository writer; use external human signing when that actor is in scope.

## [3.2.0] — Fleet-wide usage rollup

### Added

- **`adlc5 usage fleet`:** [scripts/memory/usage-ledger.py](scripts/memory/usage-ledger.py) `fleet` command aggregates `usage-ledger.jsonl` across every feature in a workspace — active `.adlc5/{feature}/` dirs plus archived snapshots under `.adlc5/_archive/` — with `totals`/`by_model`/`by_stage`/`by_feature` breakdowns and a `--active-only` flag to exclude archived features. Closes the gap where `usage summary` was scoped to a single feature and there was no workspace-wide token/cost view. Wired through the façade: `./scripts/adlc5 usage fleet --workspace . [--active-only] [--format json|markdown]`

## [3.1.0] — Docs evidence + schema_version alignment

### Added

- **Evidence + diagrams:** [docs/ADLC5.md](docs/ADLC5.md) "Why SDD-first" section + lifecycle/gate flowchart; [docs/ADLC5-kernel.md](docs/ADLC5-kernel.md) "Evidence" table + layered architecture diagram + `state set` call-path sequence diagram; [core/sdd-model.md](core/sdd-model.md) stage-status state diagram — each points at the enforcing script/file rather than asserting the strategy in prose

### Changed

- **`schema_version` aligned to the framework's 3.x line:** `"2.0"` → `"3.0"` across [core/state-schema.json](core/state-schema.json), [core/gates.yaml](core/gates.yaml), [core/personas.yaml](core/personas.yaml), [core/skill-registry.yaml](core/skill-registry.yaml), [platform/runner/runner-manifest.yaml](platform/runner/runner-manifest.yaml), [scripts/lib/state_v2.py](scripts/lib/state_v2.py), `init-feature.sh`, `pilot-autopilot.sh`. Pure relabeling — the state shape is unchanged. **Breaking for state files created before this release:** an in-flight `.adlc5/{feature}/state.json` with `schema_version: "2.0"` will fail `adlc5 state set` (`schema_version_locked`) and `pilot-autopilot.sh` (`schema 3.0 state required`) until you edit that field to `"3.0"` by hand or re-run `init-feature.sh`
- `core/skill-registry.yaml` `framework_version` and plugin manifests (`.cursor-plugin/plugin.json`, `platform/codex-plugin/plugin.json`) now track `core/VERSION` (`3.1.0`)
- `docs/ADLC5-kernel.md` retitled `ADLC5 — Fat Kernel (3.x)`; hardcoded `3.0.0` version references replaced with a pointer to `core/VERSION` so this doc doesn't go stale on the next bump

## [3.0.0] — Fat deterministic kernel façade

### Added

- **Kernel façade:** [`./scripts/adlc5`](scripts/adlc5) — `gate` / `pack` / `clarity` / `phase` / `pilot` / `state get|set` / `resolve-model` / `version`
- **Schema-validated `state set`:** [`scripts/lib/state_v2.py`](scripts/lib/state_v2.py) — merge/replace, `state-schema.json` checks, atomic write
- **Plan:** [docs/ADLC5-kernel.md](docs/ADLC5-kernel.md) (repo-root layout; VERSION = 3.0.0)
- **Path lift:** framework content moved from `v2/` to repo root (`core/`, `skills/`, `docs/`, `platform/`, `templates/`, `dogfood/`); `v2/scripts` merged into `scripts/` (`pilot-v2.sh` → `pilot-autopilot.sh`)
- Skills cite façade for spine ops (`adlc5`, `specify`, `plan`, `tasks`, `implement`, `discover`, `qa`, `deploy`, `adlc5-design-critic`)
- **Plugin metadata:** [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json), [`platform/codex-plugin/plugin.json`](platform/codex-plugin/plugin.json)

### Added (MCP + Discover)

- **MCP transport:** [`scripts/adlc5-mcp.py`](scripts/adlc5-mcp.py) — stdio tools mirror façade (`adlc5_*`); [`.cursor-plugin/mcp.json`](.cursor-plugin/mcp.json)
- **Discover prefs:** `facilitation_mode` (`ask_only` default), `assumption_policy` (`refuse` default); `council_enabled` unchanged/orthogonal

### Added (plugin packaging)

- **Cursor Agent Plugin:** [`.cursor-plugin/`](.cursor-plugin/) — `plugin.json` (`adlc5.kernel` / `adlc5.mcp`), shims `run-adlc5.sh` / `run-mcp.sh`, [README](.cursor-plugin/README.md)
- **Codex metadata:** [`platform/codex-plugin/`](platform/codex-plugin/) aligns VERSION + runtime pointers (skills still via `install.sh`)
- **`install.sh`:** prints `ADLC5_ROOT` + kernel/MCP paths; Antigravity stub records `ADLC5_ROOT` file (skills symlink behavior unchanged)

### Notes

- `phase apply` unavailable — `advance-phase.sh` is suggest-only; use `state set` after HITL
- Optional local Cursor plugin publish / A2A are next slices

## [2.1.0] — Multi-platform model profiles + agent self-update

### Added

- **`platform_profiles` + `model_routing`** in [config.example.yaml](config.example.yaml) (per-host tier IDs, `execution_policy: inherit|explicit`)
- **Resolver:** [scripts/resolve-model.sh](scripts/resolve-model.sh) + [scripts/lib/model_routing.py](scripts/lib/model_routing.py)
- **Pilot spawn JSON:** additive `recommended_model` / resolver fields from [scripts/pilot-autopilot.sh](scripts/pilot-autopilot.sh)
- **Agent self-update:** [scripts/update-adlc5.sh](scripts/update-adlc5.sh) — `--self` / `--global` / `--dry-run`
- **Per-platform model templates:** `templates/{cursor,claude,codex,opencode,hermes,gemini}-models.md`
- **Version reporting:** `install.sh` / `verify-install.sh` `--print-version` (source: `core/VERSION`)

### Changed

- Tier rename clarity: **`execution`** preferred; **`implementation`** remains a supported alias
- Default **`execution_policy: inherit`** preserves prior “inherit parent for build” behavior
- Flat **`model_profiles`** retained as fallback for unknown platforms / older configs

### Docs

- [core/guides/model-matrix.md](core/guides/model-matrix.md), [platform-tooling.md](core/guides/platform-tooling.md)
- [shared/docs/INSTALL.md](shared/docs/INSTALL.md) § Agent self-update

## [2.0.0] — ADLC5 v2 SDD-first lifecycle

### Added

- **Core:** Specify → Plan → Tasks → Implement — [docs/ADLC5.md](docs/ADLC5.md)
- **Unified state:** `schema_version: "2.0"` in `.adlc5/{feature}/state.json`
- **v2 skills:** `skills/{adlc5,specify,plan,tasks,implement}` with integrated autopilot ([scripts/pilot-autopilot.sh](scripts/pilot-autopilot.sh))
- **Memory automation:** `scripts/memory/{compact-stage,generate-pack,budget-check}`
- **Git workstreams:** [scripts/git-orchestrate.sh](scripts/git-orchestrate.sh)
- **Task visualization:** [scripts/tasks/render-board.sh](scripts/tasks/render-board.sh)
- **Quality gates wired:** `policies.autopilot.quality_gates` enforced in [scripts/check-gates.py](scripts/check-gates.py) under autonomous mode
- **Podman dev template:** [templates/podman/](templates/podman/)
- **Cloud runner stubs:** [platform/runner/](platform/runner/), [scripts/runner/dispatch.sh](scripts/runner/dispatch.sh)
- **Install:** `./scripts/install.sh `
- **Production-ready governance:** `templates/definition-of-done.md`, `skills/adlc5/governance/*` (production-ready, autopilot-stage-picker, verifier-rules).
- **Navigator:** `@adlc5` runs `check-gates.py --gate pr-ready` and mandatory AskQuestion on every invocation ([phases/00-navigator.md](skills/adlc5/SKILL.md)).
- **Gate catalog:** `assure-3-qa`, `assure-4-pr-reviewer`, policy-driven `custom_gates` / `required_gates` in `check-gates.py`.
- **Scripts:** `sync-verification-report.sh`, `scripts/lib/policies_load.py`, `scripts/lib/phase-order.sh`.
- **Pilot:** `resume_from`, `stop_at_phase`, telemetry `stage_picker` / `gate_fail`.
- **init-workspace.sh:** copies `.adlc5/governance/` and `policies.yaml.example` to consumer projects.

### Changed

- **`@adlc5-pilot` deprecated** — use `@adlc5` with `autopilot.mode: autonomous`
- **Assure:** Ladder `assure-1` … `assure-4`; `stage_status.assure: completed` requires `pr-ready` pass.
- **Verifier:** Must maintain `verify/verification-report.md`; `pass-with-warnings` requires lifecycle `verifier_waiver`.
- **README / INSTALL:** Document that forge verified ≠ production-ready.

### Docs

- [dogfood/README.md](dogfood/README.md)
- Production-ready: [scripts/check-gates.py](scripts/check-gates.py) `--gate pr-ready`
