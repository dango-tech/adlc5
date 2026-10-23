# ADLC5 — Interaction and execution modes

Two **orthogonal** preferences — do not conflate them.

## Execution mode (Implement build substep only)

Controls **how** `implement-1-build` runs story implementation.

| Field | Values | Meaning |
|-------|--------|---------|
| `defaults.execution_mode` in `policies.yaml` | `parallel` | Up to 4 `@build-implementer` subagents in parallel |
| | `sequential` | One story at a time (formerly "Manual Mode") |

**Scope:** `implement-1-build` only. Verify/integrate use **verify_policy** / **integrate_policy** (below), not execution mode.

## Verification and integration policies

Orthogonal to both execution and interaction modes. Stored as `defaults.verify_policy` and `defaults.integrate_policy` in `.adlc5/{feature}/policies.yaml`.

| Field | Values | Meaning |
|-------|--------|---------|
| `defaults.verify_policy` | `hitl` (default) | verification waits for user direction through `@adlc5-implement` |
| | `auto` | Orchestrator runs verification + rework loop per [05-verification.md](../../skills/implement/phases/01-build-through-pr.md) |
| `defaults.integrate_policy` | `hitl` (default) | integration waits for user confirmation |
| | `auto` | Orchestrator runs integration per [06-integration.md](../../skills/implement/phases/01-build-through-pr.md) |

**Default HITL is unchanged** when policies are absent: both fields default to `hitl`.

Example autopilot profile: [policies.yaml.example](../../templates/policies.yaml.example) (`verify_policy: auto`, `integrate_policy: auto`).

### Migration from `auto_mode`

| Legacy | New |
|--------|-----|
| `context.auto_mode: true` | `context.execution_mode: "parallel"` |
| `context.auto_mode: false` | `context.execution_mode: "sequential"` |

Legacy `auto_mode` may be normalized on read. New writes use only `defaults.execution_mode` in `policies.yaml`.

## Interaction mode (HITL vs autonomous)

Controls **when** the SDD must clarify ambiguities with the user.

| Field | Values | Meaning |
|-------|--------|---------|
| `autopilot.interaction_mode` in `policies.yaml` | `hitl` | Clarify unresolved consequential decisions in Specify + Plan (default) |
| | `autonomous` | Agent may record reversible nonblocking assumptions; unresolved consequential decisions still block |

**Balanced default (recommended):**

- `interaction_mode: hitl` for **Specify** and **Plan** substeps
- **Tasks / Implement:** preserve current requirement decisions; escalate new material ambiguity and reassess changed intent. Clarity scores do not waive readiness checks.

## First-run AskQuestion (orchestrator)

Collect in one form (see [askquestion-convention.md](askquestion-convention.md)):

1. `qa_log` — save Q&A log?
2. `execution_mode` — parallel vs sequential implementation
3. `interaction_mode` — HITL vs autonomous (default HITL)

Store durable policy choices in `.adlc5/{feature}/policies.yaml`; record the active autonomous/HITL mode in canonical `state.json` `autopilot.mode`.

## Navigator (`@adlc5` every invocation)

Preserve stage scope, interaction mode and target outcome already supplied by the user or recorded for this feature. Run the navigator on resume, but ask only about missing or conflicting consequential choices. See the [orchestrator](../../skills/adlc5/SKILL.md) and [requirements readiness](../../docs/requirements-readiness.md).

Autonomous mode remains part of `@adlc5`; it does not use a separate pilot skill.

## Workspace vs global install

| Artifact | Scope |
|----------|-------|
| Cursor rules (R0–R5, craftsmanship) | **Global** `~/.cursor/rules/` — generic best practices |
| Skills | **Project** via [init-workspace.sh](../../scripts/init-workspace.sh) → `.agents/skills/` |
| Feature state, config, memory | **Project** `.adlc5/` |

See [docs/INSTALL.md](../../shared/docs/INSTALL.md).

## Scaffold enforcement (Plan / Implement)

Orthogonal to execution and interaction modes. Controlled by canonical `scope.repo_profile` plus `design/scaffold-manifest.md`; waivers are recorded in `clarity.history`.

| Profile | Story 0 | Implement gate |
|---------|---------|------------|
| `greenfield` | **Required** — official scaffold from [scaffold-registry.md](scaffold-registry.md) | Component stories blocked until Story 0 `verified` |
| `brownfield` | Optional (layout standardization if user accepts drift refactor) | Paths must match manifest / existing tree |
| `waived` | — | `layout_compliance: waived` after AskQuestion (`proceed_with_custom_layout` or `scaffold_drift_waive`) |

Story 0 always runs **sequentially** in `implement-1-build` (Batch 0), even when `execution_mode: parallel`.
