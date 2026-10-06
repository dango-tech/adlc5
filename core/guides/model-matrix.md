# ADLC5 — Model profiles by stage and sub-stage

**Purpose:** Match cognitive load to model capability so lifecycle work does not under- or over-spend tokens on the wrong model.

**Config:** Prefer `platform_profiles` per host; flat `model_profiles` remains the fallback. See [config.example.yaml](../../config.example.yaml).

**Resolver (authoritative for agents):**

```bash
./scripts/resolve-model.sh --platform cursor --tier reasoning
./scripts/resolve-model.sh --tier execution --workspace . --feature my-feature
```

**Platform picker help:** [platform-tooling.md](platform-tooling.md#model-selection) · [templates/cursor-models.md](../../templates/cursor-models.md) (+ claude/codex/opencode/hermes/gemini siblings)

---

## Tiers (abstract)

| Tier | Use when | Subagent policy |
|------|----------|-----------------|
| **reasoning** | Multi-doc synthesis, security, verification gaps, council, code-spec gates | Council: one model per member (Discover). Others: inherit parent unless noted |
| **balanced** | Orchestration, structured writing, stories, integration, PR review | — |
| **execution** | Bounded TDD in listed files (`implementation` is a legacy alias) | Default **`execution_policy: inherit`** — inherit parent model; never `fast` |
| **fast** | Optional trivial routing only | **Not** for Delivery implement/verify or `@qa` |

`execution_policy` in `model_routing`:

| Policy | Behavior |
|--------|----------|
| **inherit** (default) | `execution` / `implementation` resolve like today — typically `inherit` parent session |
| **explicit** | Use concrete `platform_profiles.<host>.execution` IDs for build spawns |

**Per-feature override:** `.adlc5/{feature}/policies.yaml` may set `model_routing.execution_policy` too — it wins over the `config.yaml` global for that feature only (`resolve-model.sh --workspace . --feature NAME` picks it up; the result's `execution_policy_source` says `"feature_policy"` when it applied). This is how a cost-conscious profile opts a feature into the cheap execution tier without changing the workspace-wide default: [`templates/policies-tiny.yaml.example`](../../templates/policies-tiny.yaml.example) and [`templates/policies-standard.yaml.example`](../../templates/policies-standard.yaml.example) ship with `explicit`; [`templates/policies-high-risk.yaml.example`](../../templates/policies-high-risk.yaml.example) ships with `inherit` so the Coder session's own (reasoning-tier, per `persona_mode`) model stays on `implement-1-build`.

Resolve tier → concrete model:

```yaml
model_routing:
  strategy: cost_optimized
  execution_policy: inherit

model_profiles:          # fallback when platform unknown
  reasoning: "…"
  balanced: "…"
  implementation: "inherit"
  execution: "inherit"
  fast: "…"

platform_profiles:       # preferred when --platform is set
  cursor:
    reasoning: "auto"
    balanced: "composer-2"
    execution: "composer-2"
    fast: "composer-2-fast"
    spawn:
      task_model_param: true
```

---

## Stage × sub-stage matrix (defaults)

| Stage / skill | Sub-stage | Tier | Subagent |
|---------------|-----------|------|----------|
| `@adlc5` | Stage routing | balanced | — |
| `@adlc5-specify` | Specify pipeline | balanced | — |
| `@discover` | Council exploration / risk | reasoning | discover-council-claude, discover-council-gpt, discover-council-gemini |
| `@prt` | Phases 0–N | balanced | — |
| `@adlc5-plan` | Architecture, patterns, operations | reasoning | optional design critic |
| `@adlc5-plan` | Algorithm review (scale NFRs) | reasoning | optional autoresearch |
| `@adlc5-tasks` | User stories | balanced | — |
| `@adlc5-tasks` | TDD code specs | reasoning | — |
| `@adlc5-implement` | `implement-1-build` | execution | `@build-implementer`: inherit (unless `execution_policy: explicit`) |
| `@assure-verifier` | `implement-2-verify` | reasoning | fresh verifier for high-risk work |
| `@adlc5-implement` | Integrate / PR orchestration | balanced | — |
| `@qa` | Security / clearance | reasoning | scan subagents: inherit |
| `@pr-reviewer` | PR review | balanced | — |
| Craftsmanship S1–S10 | Per skill | balanced (S3b → reasoning) | — |

---

## Standard model notice (copy into skills)

On **first invocation** of each orchestrator/stage skill, output (replace `{skill}` and `{tier}`):

```text
Recommended model tier: {tier} ({reasoning|balanced|execution}).
Resolve with: ./scripts/resolve-model.sh --tier {tier} [--platform <host>]
See core/guides/model-matrix.md and config platform_profiles / model_profiles.
Switch your host model picker before continuing if you are on a fast/light model for this work.
(Subagents for execution/verification inherit your current model when execution_policy: inherit — do not set model: "fast".)
```

### Tier by skill (quick reference)

| Invoke | Tier |
|--------|------|
| `@adlc5`, `@adlc5-specify`, `@prt`, story decomposition in `@adlc5-tasks`, `@pr-reviewer`, S1–S10 (except S3b) | balanced |
| `@discover`, `@adlc5-plan`, TDD code specs in `@adlc5-tasks`, `@assure-verifier`, `@qa`, `@algorithm-advisor`, S3b | reasoning |
| `@adlc5-implement` build substep, `@build-implementer`, `@adlc5-tdd` | execution (alias: implementation; default inherit) |

---

## Usage tracking

After resolving a tier and completing a stage/sub-stage, record best-effort model + token
usage so it survives into the archive summary:

```bash
./scripts/adlc5 usage record --feature NAME --model-id <resolved model_id> \
  --platform <host> --tier <tier> --stage <stage> \
  --input-tokens N --output-tokens N --thinking-tokens N \
  --cache-creation-tokens N --cache-read-tokens N
```

Only pass counters the host actually reports; omit the rest (default 0). Platform-specific
counters that don't fit the standard fields (e.g. reasoning-token breakdowns, server tool
use) go in `--extra-json` rather than being dropped. See [ADLC5-kernel.md](../../docs/ADLC5-kernel.md).

`./scripts/adlc5 usage summary` / `usage fleet` attach an estimated `cost_usd` per bucket,
priced from [`core/model-prices.yaml`](../model-prices.yaml) — a periodically-refreshed
snapshot (`last_verified`), not a live billing API. A `model_id` this file doesn't recognize
(a non-Anthropic model, or a stale pin) reports `cost_usd: null` for its calls and shows up
under `unpriced_models` rather than silently costing `$0` — that gap in the table is itself
the signal to update it. Refresh the file's prices and `last_verified` whenever pricing
changes; `usage summary --format markdown` flags a snapshot over 180 days old.

## Task / spawn_agent model parameter

| Context | Rule |
|---------|------|
| `@build-implementer`, `@assure-verifier` | **Omit** `model` parameter when `execution_policy: inherit` |
| Discover council | Use platform-specific parallel agents with distinct models |
| `@qa` scan subagents | Inherit parent |
| Never | `model: "fast"` for implement, verify, code-spec, or security work |

`platform_profiles.<host>.spawn` hints (`task_model_param`, `spawn_agent_model`, `fresh_session_per_persona`) are returned by `resolve-model.sh` and included in pilot spawn JSON as `model_spawn_policy`.

---

## Cross-platform notes

| Platform | How to apply tier |
|----------|-------------------|
| **Cursor** | Model picker; [templates/cursor-models.md](../../templates/cursor-models.md) |
| **Claude Code** | `/model` — [templates/claude-models.md](../../templates/claude-models.md) |
| **Codex** | `config.toml` / spawn_agent — [templates/codex-models.md](../../templates/codex-models.md) |
| **OpenCode** | Model config — [templates/opencode-models.md](../../templates/opencode-models.md) |
| **Gemini / Antigravity** | IDE / [templates/gemini-models.md](../../templates/gemini-models.md) |
| **Hermes Agent** | Session model — [templates/hermes-models.md](../../templates/hermes-models.md) |

Concrete model IDs change frequently; keep them in **gitignored** `config.yaml`, not hardcoded in skills.

---

## Execution personas (`persona_mode`)

When `.adlc5/{feature}/policies.yaml` → `persona_mode.enabled: true`, model tiers bind to **persona identity**, not only stage skill:

| Persona | Steps | Tier | Subagent rule |
|---------|-------|------|---------------|
| Analyst | Specify, `tasks-1-stories` | balanced | — |
| Architect | Plan, `tasks-2-code-spec` | reasoning | — |
| Coder | `implement-1-build` | execution (registry may still say `implementation`) | `@build-implementer`: inherit Coder session model |
| Tester | `implement-2-verify` … `implement-5-pr` | reasoning | **`verifier_different_model: true`** → do **not** inherit Coder model for `@assure-verifier` |

Registry: [core/personas.yaml](../../core/personas.yaml)

Pilot spawn JSON includes `persona`, `fresh_session`, `verifier_different_model`, and additive `recommended_model` / resolver fields when persona mode is on.

Memory walls: [working-memory.md](working-memory.md#delivery-personas) · script: `scripts/memory/persona-pack-filter.sh`
