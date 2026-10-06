---
name: adlc5
description: ADLC5 — 4-stage SDD orchestrator (Specify → Plan → Tasks → Implement) with integrated autopilot. Invoke via @adlc5 for [feature].
version: 4.1.0
---

# ADLC5 — Orchestrator

**Single entry point** for the 4-stage SDD lifecycle with first-class autopilot.

**Invoke:** `@adlc5 for [feature]`

## SDD ladder

Specify → Plan → Tasks → Implement → `pr-ready`

Core spec: [core/sdd-model.md](../../core/sdd-model.md)

## On every invocation

1. **Framework repo guard** — lifecycle delivery belongs in consumer repos, not the adlc5 clone (unless explicit dogfood).
2. **Bootstrap** if missing state (auto-detects greenfield/brownfield and wiki need):
   ```bash
   ./scripts/init-feature.sh --feature "{feature}"
   ```
   Uses `scripts/profile-repo.py` (`--mode auto` default) and `scripts/wiki/ensure-wiki.sh` when brownfield size warrants it.
3. **Repository context** — `init-feature.sh` creates missing constitution files and
   refreshes generated intelligence. Read `AGENTS.md` and `.agents/{architecture,boundaries,commands}.yaml`;
   query `.agent-cache/repo-index.json` before searching source. Never treat cache data
   as human-approved architecture. See [repository-context.md](../../core/guides/repository-context.md).
4. Read state (schema 3.0) — note `persona.active`:
   ```bash
   ./scripts/adlc5 state get --feature "{feature}"
   ```
5. Read `memory/INDEX.md` — do not load full artifacts unless INDEX points there.
6. **Delivery Persona** — resolve from [core/personas.yaml](../../core/personas.yaml) via `current_step` or `persona.active`. Load template:
   - Analyst → `templates/personas/analyst.md`
   - Architect → `templates/personas/architect.md`
   - Coder → `templates/personas/coder.md`
   - Tester → `templates/personas/tester.md`
7. Run budget check (includes persona memory wall when `persona_mode.enabled`):
   ```bash
   ./scripts/memory/budget-check.py --feature "{feature}"
   ```
8. Run gap report:
   ```bash
   ./scripts/adlc5 gate --feature "{feature}" --gate pr-ready
   ```

When `policies.yaml` → `persona_mode.forbid_orchestrator_implement: true`, **route only** — spawn stage skills/subagents; never edit product source from the orchestrator session.

## AskQuestion (mandatory on start)

1. **Stage scope:** full lifecycle | specify only | plan only | tasks only | implement only | resume current
2. **Interaction mode:** `hitl` | `autonomous` (sets `autopilot.mode`)

See [askquestion-convention.md](../../core/guides/askquestion-convention.md).

## Stage routing

| `current_stage` | Delegate skill | Persona |
|-----------------|----------------|---------|
| `specify` | `@adlc5-specify` | Analyst |
| `plan` | `@adlc5-plan` | Architect |
| `tasks` | `@adlc5-tasks` | Analyst (`tasks-1-stories`) / Architect (`tasks-2-code-spec`) |
| `implement` | `@adlc5-implement` | Coder (`implement-1-build`) / Tester (`implement-2`…`5`) |

Persona registry: [core/personas.yaml](../../core/personas.yaml)

## Autopilot loop (integrated — replaces `@adlc5-pilot`)

When `autopilot.mode` is `autonomous` or user selects autonomous:

```text
WHILE true:
  1. ./scripts/pilot-check-kill-switch.sh --feature F
  2. OUT=$(./scripts/adlc5 pilot --feature F)
  3. Parse OUT.action:
     spawn   → invoke skill from OUT.skill; on completion ./scripts/adlc5 pilot --feature F --record-result pass|fail
     advance → confirm via ./scripts/adlc5 phase --feature F; update state; continue
     heal    → reworker / retry recipe; continue
     halt    → AskQuestion or STOP file; EXIT
     done    → pr-ready handoff; EXIT
```

Cost-aware profiles in `.adlc5/{feature}/policies.yaml`: `tiny`, `standard`,
`high_risk`. Legacy profiles remain valid and retain the full path.

**Deprecated:** `@adlc5-pilot` — use `@adlc5` with autonomous mode.

## Soul check (fifth pillar — before every gate)

Before running any gate below, emit the 5-line graph-aware check from [@adlc5-soul](../adlc5-soul/SKILL.md): preserve acceptance, use code/graph evidence, choose the minimum sufficient profile, honor dependency/file ownership and trust boundaries, then require independent quality evidence before cost optimization. Verdict: `proceed | refocus | defer`. Advisory only: it never replaces the gate. On `refocus`/`defer` in HITL, AskQuestion; autonomous, record in `memory/summaries/{stage}.md` and act per verdict.

For volatile technology facts, route Specify/Plan through [current-information.md](../../core/guides/current-information.md): verify official sources at task time and do not ship stale version, status, API, protocol, or security claims.

## Hard gates

| Transition | Gate |
|------------|------|
| Specify → Plan | `specify-complete` |
| Plan → Tasks | `plan-complete` |
| Tasks stories → code spec | `tasks-1-stories-complete` |
| Tasks → Implement | `tasks-2-code-spec-complete` / `tasks-complete` |
| Feature done | `pr-ready` |

## State schema

[core/state-schema.json](../../core/state-schema.json)

## Scripts (mantra)

Skills route; **prefer kernel façade** `./scripts/adlc5` for spine ops (`gate`, `phase`, `pilot`, `state get|set`, `pack`, `clarity`, `resolve-model`) — see [ADLC5-kernel.md](../../docs/ADLC5-kernel.md) and [gates.yaml](../../core/gates.yaml). Apply phase changes with `state set --patch` after `phase` confirms ready (advance-phase is suggest-only).

## Cross-platform

[platform/README.md](../../platform/README.md) · [CROSS-PLATFORM.md](../../shared/docs/CROSS-PLATFORM.md)

## Model recommendation

**Tier:** balanced (orchestration). Resolve host model:

```bash
./scripts/adlc5 resolve-model --tier balanced [--platform <host>]
```

See [model-matrix.md](../../core/guides/model-matrix.md) and `platform_profiles` / `model_profiles` in config. Never use `fast` for implement/verify or `@qa`.
