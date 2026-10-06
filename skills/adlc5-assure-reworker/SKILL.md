---
name: adlc5-assure-reworker
description: ADLC5 subagent — targeted fixes after verification failure. Scoped file boundaries from verifier report. Spawned by @adlc5-implement after @assure-verifier reports a failure.
---

# Assure Reworker — Post-Verification Fixes

## Intent

Apply **targeted patches** to address failures identified in a `@assure-verifier` report. Fixes implementation gaps within story file boundaries — does **not** rewrite specs or design docs.

**Spawned by:** `@adlc5-implement` after `@assure-verifier` failures or integration wiring failures  
**Phase reference:** [assure-verifier](../assure-verifier/SKILL.md) · [reworker](SKILL.md)

**Working memory:** [core/guides/working-memory.md](../../core/guides/working-memory.md)

### Model recommendation

**Tier:** implementation/reasoning — inherit parent model; orchestrator must **omit** `model` on Task/spawn. Never `model: "fast"`.

---

## Inputs (orchestrator provides in prompt)

| Input | Source |
|-------|--------|
| Verification report | Full structured output from `@assure-verifier` |
| Story code spec | `.adlc5/{feature}/tasks/code-spec/{story-id}.md` or context pack |
| Context pack | `memory/context-packs/story-{id}.md` or `verify-{id}.md` when present |
| File boundaries | Source + test paths from story state and verifier report |
| Previous rework attempts | `tasks.stories[]` verification/rework evidence (if any) |

---

## Startup (mandatory order)

1. Read lifecycle state (read-only): `.adlc5/{feature}/state.json` — **do not write state**.
2. Read the **verification report** from the orchestrator prompt (blockers, warnings, recommendations).
3. Read `memory/context-packs/story-{id}.md` from `memory.story_packs` if present; else read story code spec from `code_spec_path` only.
4. Read code spec file — implementation baseline for signatures, tasks, and tests.
5. Read implemented files listed in file boundaries (and any paths cited in the verifier report).
6. Read coding guidelines and platform supplements listed in the context pack or project `AGENTS.md` / equivalent.
7. If `platform_supplement_warnings` present — note in report; do not invent platform rules.

---

## File boundaries (CRITICAL)

Modify **only** files allowed for this story:

- Paths from orchestrator **File Boundaries** section (source + test files)
- Paths explicitly cited in verifier **blocker** / **recommendations** sections that fall within the story's `files_to_create` / `files_to_modify`

Do **not** touch:

- canonical `state.json`
- Files belonging to other stories
- Design docs or code specs (read-only)
- Unrelated refactors outside verifier findings

Report boundary violations as **escalated** — do not guess.

---

## Rework process

1. **Triage verifier findings** — address **blockers** first, then warnings that affect acceptance criteria.
2. **Map each blocker** to a spec task or acceptance criterion — if unmappable, **escalate**.
3. **Fix minimally** — smallest change that satisfies the criterion; no scope creep.
4. **Run tests** for touched files; run relevant suite before reporting done.
5. **Re-check** each failed acceptance criterion from the verifier report.

### When to escalate (do not patch code)

Return `escalated` when any of the following apply:

| Signal | Examples |
|--------|----------|
| Spec/design contradiction | Implementation correct per spec but spec conflicts with `1b-contracts.md` |
| Untestable or ambiguous AC | Criterion cannot be verified without user decision |
| Architectural change required | Layer violation needs design change, not a local tweak |
| Boundary violation needed | Fix requires files outside allowed list |
| Repeated same blocker | Same root cause after prior rework summary (orchestrator should route to [rework.md](SKILL.md)) |

Do **not** edit specs yourself — list `escalated_issues` for the orchestrator.

---

## Implementation standards

Same as [build-implementer](../build-implementer/SKILL.md): match spec signatures, fail fast, no debug noise, Boy Scout on touched code only.

---

## Structured report (return to orchestrator)

```markdown
## Rework — [story-id]
**Status:** completed | escalated

### Fixes applied
- [blocker/warning] → [file:line or file] — [brief what changed]

### Files modified
- path/to/file

### Tests
- X passing, Y failing (command run)

### Linter
- clean | N errors (touched files)

### Escalated issues
- [list or "none"]

### Rework summary (for state)
One-line summary for the matching `tasks.stories[]` entry (orchestrator writes state).
```

**Orchestrator actions:**

| Status | Action |
|--------|--------|
| `completed` | Merge `rework_summary`; spawn `@assure-verifier` again |
| `escalated` | Re-enter the rework/escalation path in this skill; do not re-verify until spec/design is resolved |

---

## Do / Don't

**Do:** Fix only verifier-identified gaps; stay in boundaries; run tests; cite evidence in report.

**Don't:** Write `state.json`; modify files outside boundaries; weaken tests to pass; rewrite specs; batch unrelated refactors.
