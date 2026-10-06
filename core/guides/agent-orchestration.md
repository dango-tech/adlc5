# ADLC5 — AI agent products (orchestration guide)

**When to use:** The feature builds or extends an **AI agent** (tools, multi-step reasoning, sub-agents, eval, release) — not only “we used Cursor to write the code.”

**Concepts (vendor-neutral):** [../knowledge-base/07-ai-agent-orchestration.md](../../shared/docs/knowledge-base/07-ai-agent-orchestration.md)

**Stack-specific scaffold** (optional): [scaffold-registry.md](scaffold-registry.md) — e.g. official CLI for a detected framework. Registry entries are **adapters**, not architecture law.

Volatile protocol/version claims must follow [current-information.md](current-information.md): recheck official sources before use, record the verification date/status, and never treat this snapshot as live documentation.

---

## Current A2UI status

**last_verified:** 2026-08-28 · **production:** v0.9.1 (stable) · **next:** v1.0 (release candidate)

A2UI is a declarative, JSON-based streaming protocol for an agent to describe UI structure and data that a host renderer maps to trusted native components. The official project describes the overall ecosystem as an early-stage public preview, says v0.9.1 is the current stable protocol release, and says v1.0 is a release candidate; do not describe v1.0 as final or use it as the production default without an explicit candidate-adoption decision.[1][3][4]

The v1.0 candidate introduces role-based bidirectional function calls, optional single-message surface creation, mixed catalogs, and stricter identifiers/accessibility. Its migration guide removes `theme` and `primaryColor` from protocol/catalog payloads: branding belongs to the renderer and the application's design system, not to A2UI wire messages.[1][2]

Use A2UI only when an agent must describe portable UI for a host-owned renderer. It does not replace product UI architecture, branding tokens, AG-UI/A2A/MCP transports, authentication, authorization, or accessibility implementation. Keep protocol adapters version-isolated so v0.9.1 production support and v1.0 candidate experiments cannot silently mix.

---

## How ADLC5 already orchestrates AI agents (delivery layer)

ADLC5 is **L2 delivery orchestration** (see concepts doc §1). It does not replace your agent runtime (L3).

| Concept (§5–6) | ADLC5 mechanism |
|----------------|-----------------|
| Supervisor + workers | `@adlc5-implement` spawns `@build-implementer` (max 4 parallel) |
| Evaluator loop | `@assure-verifier` + `@adlc5-assure-reworker` |
| Council / ensemble | `@discover` LLM council ([discover/phases/01-exploration.md](../../skills/discover/phases/01-exploration.md)) |
| Human-in-the-loop | AskQuestion, clarity gate, `interaction_mode: hitl` |
| Autopilot supervisor | `@adlc5 autonomous mode` + `scripts/pilot-autopilot.sh` |
| Minimal worker context | [working-memory.md](working-memory.md) context packs |
| Model tiers | [model-matrix.md](model-matrix.md) |
| Host spawn API | [platform-tooling.md](platform-tooling.md) (`Task`, `spawn_agent`) |
| Token/cost observability (§8) | `scripts/memory/usage-ledger.py` — `adlc5 usage record` (per-call), `usage summary` (per-feature), `usage fleet` (workspace-wide). Worked reference for the per-call → session → fleet rollup pattern — apply the same shape to the agent product's own LLM calls, not just to ADLC5's delivery work |

---

## Lifecycle mapping (agent *product*)

Use this table in Spec/PRT and Delivery design — cite section ids from [07-ai-agent-orchestration.md](../../shared/docs/knowledge-base/07-ai-agent-orchestration.md).

| Agent product phase | ADLC5 stage | Primary invokes |
|---------------------|-------------|-----------------|
| Frame | Specify | `@discover`, `@prt`, `@adlc5-specify` |
| Scaffold (greenfield) | Plan Story 0 | Registry `official_scaffold` + manifest |
| Implement runtime | Implement | `@adlc5-implement`, `@build-implementer`, `@adlc5-tdd` |
| Evaluate | Plan + Implement/Verify | Code spec eval stories; `@qa`; optional eval scripts in repo |
| Release | Implement / post-PR | Document in ops design (1c); stack adapter CLI if any |
| Observe | Plan 1c | Ops doc: traces, logs, SLOs |
| Govern | Specify + Implement | Policies, kill-switch, `@adlc5 autonomous mode` budgets |

---

## Plan checklist (agent features)

Copy into `.adlc5/{feature}/design/` or PRD when `product_type: agent`:

- [ ] **L3 pattern** named (single / supervisor-workers / pipeline / council) — §5
- [ ] **Tools** listed with contracts and idempotency
- [ ] **State** model: session vs thread vs durable workflow
- [ ] **HITL** gates documented
- [ ] **Eval**: metrics, eval set location, baseline, pass threshold — §6
- [ ] **Release**: artifact type, runtime attachment (abstract), rollback — §7
- [ ] **Observability**: correlation id, required spans/logs — §8
- [ ] **Token/cost collection**: per-call ledger (model, tokens by type, session id), session rollup, budget enforcement tied to a real control (warn/block/kill-switch) — §8 pattern; see the ADLC5 mechanism row above for a worked reference
- [ ] **Story 0** uses registry scaffold if greenfield — [scaffold-registry.md](scaffold-registry.md)
- [ ] **No vendor** named in core design unless user chose a stack (adapter only)

Template: [templates/agent-product/spec-checklist.md](../../templates/agent-product/spec-checklist.md)

---

## Scripts over prompts

| Repeatable action | Belongs in |
|-------------------|------------|
| `agents-cli scaffold` (or any official CLI) | Invoked by skill; command recorded in `scaffold-manifest.md` |
| Eval run, lint agent project | `scripts/` in **consumer repo** |
| Pilot loop, gate checks | `scripts/pilot-autopilot.sh`, `scripts/check-gates.py` (ADLC5 distro) |

Skills route and interpret SDD; they do not embed long shell pipelines ([adlc5-sdd-mantra](../../.cursor/rules/adlc5-sdd-mantra.mdc)).

---

## What ADLC5 does not provide (by design)

- A vendor-neutral **agent runtime** (you pick L3: framework or custom)
- Managed **cloud deploy** skills (use registry adapter + your platform docs)
- Replacement for framework docs (wrap at boundaries; learning tests in consumer repo)

For stack-specific agent CLIs, add a **registry row** in [scaffold-registry.md](scaffold-registry.md) — keep [07-ai-agent-orchestration.md](../../shared/docs/knowledge-base/07-ai-agent-orchestration.md) free of cloud names.

---

## Invoke quick reference

| Intent | Invoke |
|--------|--------|
| Full feature (agent or not) | `@adlc5` |
| Exploration / council | `@discover` |
| Architecture before agent code | `@adlc5-plan`, `@clean-architecture-review` |
| Design + stories + code spec | `@adlc5-plan` |
| Parallel implement | `@adlc5-implement` |
| Autopilot to PR-ready | `@adlc5 autonomous mode` |
| Brownfield repo context | `@adlc5-project-wiki` (optional) |

## Sources

[1] [A2UI Protocol v1.0 — Candidate](https://a2ui.org/specification/v1.0-a2ui/)
[2] [A2UI Evolution Guide v0.9.1 → v1.0](https://a2ui.org/specification/v1.0-evolution-guide/)
[3] [A2UI Roadmap](https://a2ui.org/roadmap/)
[4] [A2UI official repository README](https://github.com/a2ui-project/a2ui/blob/main/README.md)
