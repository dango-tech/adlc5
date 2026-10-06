# ADLC5 — Legacy phase alias registry

Compatibility reference for pre-v3 five-stage and delivery `current_phase` aliases. The canonical v3 lifecycle and step IDs are defined by [sdd-model.md](../sdd-model.md), [state-schema.json](../state-schema.json), and `CANONICAL_STEPS` in `scripts/lib/policies_load.py`.

> Do not write the five-stage IDs below into canonical v3 `state.json`. Routers may read them only from legacy delivery state and normalize them to v3 Specify → Plan → Tasks → Implement steps.

**Legacy lifecycle represented below:** **Spec → Engineering → Plan → Build → Assure**

**Scaffold / layout:** [scaffold-registry.md](scaffold-registry.md) — repo profile, Story 0, `scaffold-manifest.md`, Build gates.

## Naming convention

- **Step ID:** `{pipeline}-{n}-{slug}` (e.g. `plan-1-discovery`)
- **Display label:** `Stage 3 — Plan · Step 1 — Design Discovery`
- **Resume line:** announce display label + clarity score (see [clarity-scoring.md](clarity-scoring.md))

Store optional `current_phase_display` in state when resuming.

---

## Legacy ADLC5 lifecycle (five stages)

| Stage | `current_stage` | Display | Purpose |
|-------|-----------------|---------|---------|
| 1 | `spec` | Spec | Requirements, AC, scale NFRs |
| 2 | `engineering` | Engineering | Architecture, patterns, algorithms |
| 3 | `plan` | Plan | Design, stories, TDD-ready code specs |
| 4 | `build` | Build | Implementation (TDD) |
| 5 | `assure` | Assure | Verify, integrate, QA, PR |

---

## Workflow ladder (cheat sheet)

```
Stage 1 — Spec
  spec-0-git-isolation       → .adlc5/{feature}/state.json (git.*)
  spec-1-discover            → .discover/{feature}/discovery-brief.md  (optional)
  spec-2-requirements        → .prt/{feature}/prt.md
  spec-3-nfr-capture         → .adlc5/{feature}/state.json (scale_nfrs.*)
  spec-4-exit                → .adlc5/{feature}/spec-handoff.md

Stage 2 — Engineering
  engineering-1-architecture-review  → craftsmanship.architecture_review
  engineering-2-pattern-selection    → craftsmanship.pattern_selection
  engineering-3-algorithm-review     → craftsmanship.algorithm_review (if scale NFRs)
  engineering-4-pattern-opportunity  → S4 output
  engineering-5-exit                 → memory/summaries/engineering.md

Stage 3 — Plan (Delivery)
  plan-1-discovery           → .adlc5/{feature}/design/1a-discovery.md, scaffold-manifest.md
  plan-2-contracts           → .adlc5/{feature}/design/1b-contracts.md
  plan-3-operations          → .adlc5/{feature}/design/1c-operations.md
  plan-4-user-stories        → .adlc5/{feature}/delivery/state.json (stories; story-0-scaffold-foundation when greenfield)
  plan-5-code-spec           → .adlc5/{feature}/delivery/code-spec/

Stage 4 — Build (Delivery)
  build-1-implementation     → source + tests per story

Stage 5 — Assure (Delivery + pipeline)
  assure-1-verification      → verifier reports per story
  assure-2-integration       → integration story / E2E (parallel execution mode)
  assure-3-qa                → .qa/{feature}/deployment-clearance.md
  assure-4-pr-reviewer         → @pr-reviewer
```

Artifact filenames (`1a-discovery.md`, etc.) are stable for one release. The IDs below are canonical only within legacy delivery state; canonical v3 uses `current_step` from `state.json`.

---

## Delivery (`.adlc5/{feature}/delivery/state.json`)

| Legacy `current_phase` | Canonical `current_phase` | Display label | `phase_status` key |
|------------------------|-------------------------|---------------|-------------------|
| `1a`, `plan-1-discovery` | `plan-1-discovery` | Design Discovery | `plan_discovery` |
| `1b`, `plan-2-contracts` | `plan-2-contracts` | API & Integration Contracts | `plan_contracts` |
| `1c`, `plan-3-operations` | `plan-3-operations` | Security, Performance & Ops | `plan_operations` |
| `2`, `plan-4-user-stories` | `plan-4-user-stories` | User Stories | `plan_user_stories` |
| `3`, `plan-5-code-spec` | `plan-5-code-spec` | Code Spec (TDD plans) | `plan_code_spec` |
| `4` | `build-1-implementation` | Implementation (TDD) | `build_implementation` |
| `5` | `assure-1-verification` | Verification | `assure_verification` |
| `6` | `assure-2-integration` | Integration & E2E | `assure_integration` |
| `completed` | `completed` | Feature complete | — |

**Phase guides:** [skills/adlc5-plan/phases/](../../skills/plan/phases) (filenames unchanged; headers use display labels).

**Legacy `phase_status` keys:** `design_1a`, `design_1b`, `design_1c`, `user_stories`, `code_spec`, `specify_*` — normalize on read to `plan_*` keys above.

---

## Spec sub-pipeline ([adlc5-spec](../../skills/specify/SKILL.md))

| Step ID | Display label | Phase doc |
|---------|---------------|-----------|
| `spec-0-git-isolation` | Git Isolation | [00-git-isolation.md](../../skills/specify/phases/00-git.md) |
| `spec-1-discover` | Problem Discovery (optional) | [01-discover.md](../../skills/specify/phases/01-discover.md) |
| `spec-2-requirements` | Requirements (PRT) | [02-prt.md](../../skills/specify/phases/02-requirements.md) |
| `spec-3-nfr-capture` | Scale NFRs | [03-nfr-capture.md](../../skills/specify/phases/03-nfr.md) |
| `spec-4-exit` | Spec Handoff | [04-exit.md](../../skills/specify/phases/04-handoff.md) |

State field: `spec.current_step`

---

## Discover (`.discover/{topic}/state.json`)

| Legacy | New ID | Display label |
|--------|--------|---------------|
| `0` | `discover-0-problem-framing` | Problem Framing |
| `1` | `discover-1-council-exploration` | Council Exploration |
| `1b` | `discover-2-synthesis-review` | Synthesis Review |
| `2` | `discover-3-direction-setting` | Direction Setting |
| `2b` | `discover-4-risk-challenge` | Risk Challenge |
| `3` | `discover-5-discovery-brief` | Discovery Brief |

---

## PRT (`.prt/{feature}/state.json`)

| Legacy | New ID | Display label |
|--------|--------|---------------|
| `0` | `prt-0-intake` | Intake |
| `1a` | `prt-1-requirements-draft` | Requirements Draft |
| `1b` | `prt-2-requirements-review` | Requirements Review |
| `2` | `prt-3-ux-ideation` | UX Ideation |
| `3` | `prt-4-epic-breakdown` | Epic Breakdown |

---

## Engineering ([adlc5-engineering](../../skills/plan/SKILL.md))

| Step ID | Display label |
|---------|---------------|
| `engineering-1-architecture-review` | Architecture Review (S2) |
| `engineering-2-pattern-selection` | Pattern Selection (S3/S5) |
| `engineering-3-algorithm-review` | Algorithm Review (S3b) |
| `engineering-4-pattern-opportunity` | Pattern Opportunity (S4) |
| `engineering-5-exit` | Engineering Handoff |

State field: `engineering.current_step` · `current_stage` is `engineering` (display: **Engineering**).

---

## QA (`.qa/{feature}/state.json`)

| Legacy | New ID | Display label |
|--------|--------|---------------|
| `0` | `qa-0-test-discovery` | Test Discovery |
| `1` | `qa-1-security-scanning` | Security Scanning |
| `2` | `qa-2-quality-gate` | Quality Gate |
| `3` | `qa-3-performance-accessibility` | Performance & Accessibility |
| `4` | `qa-4-compliance` | Compliance & Clearance |

`phase_status` keys unchanged (`test_discovery`, `security_scanning`, etc.).

---

## Legacy alias map (normalize on read)

Legacy delivery routers MUST apply this map when loading `delivery/state.json` and write **plan-*** compatibility IDs only. Canonical v3 routers write the four-stage `current_step` IDs.

```json
{
  "1a": "plan-1-discovery",
  "1b": "plan-2-contracts",
  "1c": "plan-3-operations",
  "2": "plan-4-user-stories",
  "3": "plan-5-code-spec",
  "plan-1-discovery": "plan-1-discovery",
  "plan-2-contracts": "plan-2-contracts",
  "plan-3-operations": "plan-3-operations",
  "plan-4-user-stories": "plan-4-user-stories",
  "plan-5-code-spec": "plan-5-code-spec",
  "4": "build-1-implementation",
  "5": "assure-1-verification",
  "6": "assure-2-integration",
  "0": "context-dependent",
  "1": "context-dependent",
  "1b_discover": "discover-2-synthesis-review",
  "2b": "discover-4-risk-challenge"
}
```

**Lifecycle stage:** `current_stage: "plan"` → normalize to `"plan"` on read.

**Ambiguous numerics (`0`, `1`, `2`):** resolve using pipeline context — parent state file path (`.discover/` vs `.prt/` vs `.qa/` vs delivery) or `current_stage` in `.adlc5/{feature}/state.json`.

### Delivery `phase_status` legacy aliases

| Legacy key | Canonical key |
|------------|---------------|
| `design_1a` | `plan_discovery` |
| `design_1b` | `plan_contracts` |
| `design_1c` | `plan_operations` |
| `user_stories` | `plan_user_stories` |
| `code_spec` | `plan_code_spec` |
| `plan_discovery` | `plan_discovery` |
| `plan_contracts` | `plan_contracts` |
| `plan_operations` | `plan_operations` |
| `plan_user_stories` | `plan_user_stories` |
| `plan_code_spec` | `plan_code_spec` |
| `implementation` | `build_implementation` |
| `verification` | `assure_verification` |
| `integration` | `assure_integration` |

---

## Resume announcement template

```
Resuming: Stage 3 — Plan · Step 2 — API & Integration Contracts
Clarity: 72/80 (1 open item) · Interaction: HITL · Execution: parallel
Next: complete plan-2-contracts → .adlc5/{feature}/design/1b-contracts.md
```

---

## Appendix — Gate catalog (`check-gates.py`)

| Gate ID | When to run | Exit meaning |
|---------|-------------|--------------|
| `plan-1-discovery` … `plan-5-code-spec` | After each Plan step | Phase artifact + `phase_status` |
| `plan-phase` | Pilot/router on Plan 1–3 | Resolves to `current_phase` |
| `build-1-implementation` | Before Build complete | All stories `implementation_complete`+ |
| `assure-1-verification` | Before integration / verification complete | Stories `verified` + report sync |
| `assure-2-integration` | Before delivery `completed` | `integration.status: completed` |
| `assure-3-qa` | Assure ladder step 3 | QA clearance **CLEARED** (fail if missing/BLOCKED) |
| `assure-4-pr-reviewer` | Assure ladder step 4 | `assure.pr_review` or `pr_review.url` |
| `pr-ready` | Before `stage_status.assure: completed` | Delivery complete + QA + verification + custom `required_gates` |

Legacy gate IDs `specify-*` and `plan-phase` are accepted and normalized to `plan-*`.

**Scripts:** `scripts/check-gates.py`, `scripts/sync-verification-report.sh`  
**Policies:** `.adlc5/{feature}/policies.yaml` → `custom_gates`, `required_gates`  
**Production-ready:** [governance/production-ready.md](../governance/production-ready.md)

---

## Skills referencing this guide

- [skills/adlc5/SKILL.md](../../skills/adlc5/SKILL.md)
- [skills/adlc5-spec/SKILL.md](../../skills/specify/SKILL.md)
- [skills/adlc5-plan/SKILL.md](../../skills/plan/SKILL.md)
- [skills/discover/SKILL.md](../../skills/discover/SKILL.md)
- [skills/prt/SKILL.md](../../skills/prt/SKILL.md)
- [skills/qa/SKILL.md](../../skills/qa/SKILL.md)
