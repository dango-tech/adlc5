---
name: adlc5-specify
description: ADLC5 Stage 1 Specify — git isolation, optional @discover/@prt, NFR capture, spec-handoff. Invoke via @adlc5-specify.
version: 4.1.0
---

# ADLC5 — Specify

**Stage 1** of the 4-stage SDD ladder: Specify → Plan → Tasks → Implement.

**Invoke:** `@adlc5-specify for [feature]`

**Persona:** Analyst — load [templates/personas/analyst.md](../../templates/personas/analyst.md) at startup. Memory wall: no `design/`, `tasks/code-spec/`, or product `src/`.

If `.adlc5/{feature}/state.json` is missing:

```bash
./scripts/init-feature.sh --feature "{feature}" [--mode greenfield|brownfield] [--interaction hitl|autonomous]
```

Before requirements capture, read `AGENTS.md` and the tracked `.agents/` constitution
for existing constraints. Do not infer new architecture from `.agent-cache/`; it is
generated navigation evidence, not human-approved intent.

## Step ladder

| Step | Doc | Purpose |
|------|-----|---------|
| `specify-0-git` | [phases/00-git.md](phases/00-git.md) | Git isolation |
| `specify-1-discover` | [phases/01-discover.md](phases/01-discover.md) | Optional `@discover` |
| `specify-2-requirements` | [phases/02-requirements.md](phases/02-requirements.md) | `@prt` or inline reqs |
| `specify-3-nfr` | [phases/03-nfr.md](phases/03-nfr.md) | Scale NFRs + enterprise NFR/compliance checklist |
| `specify-4-handoff` | [phases/04-handoff.md](phases/04-handoff.md) | `spec-handoff.md` |

For the `tiny` profile, run `specify-0-git` and write a minimal,
user-checkable `spec-handoff.md`; skip Discover, PRT, and scale-NFR ceremony.
Other profiles retain the full Specify ladder.

## Current information

When requirements depend on a version, protocol status, API, provider capability,
security recommendation, or current best practice, verify it against an official
primary source during this task and record `last_verified`, status, and source
URLs. Stale or unverified load-bearing claims block handoff. Follow
[current-information.md](../../core/guides/current-information.md).

## Gates

Before leaving Specify:

```bash
./scripts/adlc5 gate --feature "{feature}" --gate specify-complete
./scripts/memory/compact-stage.sh --feature "{feature}" --stage specify
```

## State

Unified state (schema 3.0) only — see [core/state-schema.json](../../core/state-schema.json).

Update `current_step`, `stage_status.specify`, `git`, `scale_nfrs`, `clarity`.

## AskQuestion (mandatory on start)

1. Scope: `epic` | `increment` | `spike`
2. Git: `branch` | `worktree` | `current` | `skip`

See [askquestion-convention.md](../../core/guides/askquestion-convention.md).

## Working memory

On stage complete: `./scripts/memory/compact-stage.sh --stage specify`

Read `memory/INDEX.md` first on every invocation.

OKF pattern catalog is **not** L1 memory — do not load `shared/docs/patterns/` during Specify unless tagging NFRs for later Plan lookup.
