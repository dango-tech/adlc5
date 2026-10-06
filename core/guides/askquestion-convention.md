# ADLC5 — Structured user choices (Q&A)

**Mandatory for all `@adlc5*` skills** (orchestrator, stage runners, and pipeline skills invoked from Specify/Implement).

When you need a **decision, preference, confirmation, or structured choice**, use the host’s **structured Q&A UI** when available. **Do not** use vague “yes or no in chat” when finite options exist.

| Platform | Mechanism |
|----------|-----------|
| **Cursor** | `AskQuestion` tool (Q&A form) |
| **Claude Code** | `AskUserQuestion` if available |
| **Codex** | `request_user_input` / approval UI |
| **OpenCode** | permission `ask` or skill tool |
| **Gemini / Antigravity** | native choice UI when present |
| **Fallback (all)** | Numbered options in chat — same `option.id` labels as below |

Full tool mapping: [platform-tooling.md](platform-tooling.md).

## When to use structured Q&A

| Use structured Q&A | Use chat (rare) |
|-----------------|-----------------|
| Yes / No / Skip | Open-ended creative input (problem description, feature name from vague idea) |
| Pick one of 2–6 options | Paste a file path or PRD the user already has |
| Multi-select (personas, stories) | Long narrative answers during discovery interview |
| Phase advance confirmation | User explicitly said "just do it" / waived gates |
| Waive a gate with documented reason | — |

**Batching:** Prefer **one form with 1–2 questions** over many tiny prompts. Max **2 questions per call** unless the skill phase explicitly requires a multi-step wizard.

## How to invoke (Cursor: AskQuestion)

On **Cursor**, call the **AskQuestion** tool. On **other platforms**, use the equivalent from [platform-tooling.md](platform-tooling.md) or the **fallback** numbered list with the same option ids.

Each question needs:

- `id` — stable slug (e.g. `qa_log`, `advance_phase`)
- `prompt` — clear question text
- `options` — array of `{ "id": "...", "label": "..." }` (2–6 options)
- `allow_multiple` — `true` only when multi-select is intended

### Example — Git isolation before Specify (two questions, one call)

Run **before** `@discover`, `@prt`, or any requirements artifact. See [git-isolation.md](git-isolation.md).

```json
{
  "title": "ADLC5 — Git isolation",
  "questions": [
    {
      "id": "git_isolation",
      "prompt": "How should we isolate git work for this feature? (Current branch: main)",
      "options": [
        { "id": "branch", "label": "Create feature branch feat/my-feature and check out here" },
        { "id": "worktree", "label": "Add worktree + branch (separate directory)" },
        { "id": "current", "label": "Stay on current branch (main)" },
        { "id": "skip", "label": "Skip — I manage branches / not using git" }
      ]
    },
    {
      "id": "branch_name",
      "prompt": "Branch name?",
      "options": [
        { "id": "default", "label": "Use feat/my-feature" },
        { "id": "custom", "label": "Custom name (reply in chat)" }
      ]
    }
  ]
}
```

Omit question 2 when `git_isolation` is `current` or `skip`.

### Example — ADLC5 first-run preferences (two calls, max 2 questions each)

Call 1:

```json
{
  "title": "ADLC5 setup",
  "questions": [
    {
      "id": "qa_log",
      "prompt": "Save a Q&A log (qa-log.md) for this feature?",
      "options": [
        { "id": "yes", "label": "Yes — save Q&A log (recommended for teams)" },
        { "id": "no", "label": "No — skip Q&A logging" }
      ]
    },
    {
      "id": "execution_mode",
      "prompt": "Implement build style?",
      "options": [
        { "id": "parallel", "label": "Parallel — up to 4 story subagents" },
        { "id": "sequential", "label": "Sequential — one story at a time" }
      ]
    }
  ]
}
```

Call 2:

```json
{
  "questions": [
    {
      "id": "interaction_mode",
      "prompt": "How should ADLC5 engage you during Specify and Plan?",
      "options": [
        { "id": "hitl", "label": "HITL — clarify ambiguities before advancing (recommended)" },
        { "id": "autonomous", "label": "Autonomous — proceed with documented assumptions" }
      ]
    }
  ]
}
```

Map `execution_mode` → `policies.yaml` `defaults.execution_mode`.

### Example — Clarity clarification batch

```json
{
  "title": "ADLC5 — Clarify requirements",
  "questions": [
    {
      "id": "clarify_ac",
      "prompt": "FR-003 says 'filter by status' — which status values apply?",
      "options": [
        { "id": "draft_active_archived", "label": "draft, active, archived" },
        { "id": "custom", "label": "Custom list (reply in chat)" },
        { "id": "proceed_assumptions", "label": "Proceed with documented assumptions" }
      ]
    }
  ]
}
```

### Example — Phase advance (single question)

```json
{
  "questions": [
    {
      "id": "advance_phase",
      "prompt": "Plan Step 1 — Design Discovery complete (clarity 85/80). Ready for Step 2 — API & Integration Contracts?",
      "options": [
        { "id": "yes", "label": "Yes — continue to Contracts" },
        { "id": "revise", "label": "Revise Design Discovery first" },
        { "id": "pause", "label": "Pause — resume later" }
      ]
    }
  ]
}
```

### Example — Resume existing feature

```json
{
  "questions": [
    {
      "id": "select_feature",
      "prompt": "Which ADLC5 feature should we continue?",
      "options": [
        { "id": "feature-a", "label": "feature-a (Stage: plan)" },
        { "id": "feature-b", "label": "feature-b (Step: implement-1-build)" },
        { "id": "new", "label": "Start a new feature instead" }
      ]
    }
  ]
}
```

### Example — Ambiguous repo profile (scaffold)

```json
{
  "title": "ADLC5 — Repo profile",
  "questions": [
    {
      "id": "repo_profile_choice",
      "prompt": "This repo has minimal source (1–2 files, no tests). How should we treat it?",
      "options": [
        { "id": "greenfield_scaffold", "label": "Greenfield — run official scaffold (Story 0) then feature work" },
        { "id": "brownfield_extend", "label": "Brownfield — extend existing paths only (no Story 0)" }
      ]
    }
  ]
}
```

Map `greenfield_scaffold` → `scope.repo_profile: greenfield`; `brownfield_extend` → `brownfield`.

### Example — Brownfield layout drift

```json
{
  "questions": [
    {
      "id": "scaffold_drift_action",
      "prompt": "Layout differs from [stack] standard in scaffold-registry. What should we do?",
      "options": [
        { "id": "scaffold_drift_refactor", "label": "Refactor toward standard — add Story 0 Layout Standardization" },
        { "id": "scaffold_drift_document", "label": "Document deviations in scaffold-manifest only" },
        { "id": "scaffold_drift_waive", "label": "Waive — keep current layout (layout_compliance: waived)" }
      ]
    }
  ]
}
```

### Example — Custom layout waiver (greenfield)

```json
{
  "questions": [
    {
      "id": "proceed_with_custom_layout",
      "prompt": "Registry has an official scaffold for this stack. Proceed with a hand-built layout instead?",
      "options": [
        { "id": "use_official_scaffold", "label": "No — use official scaffold (Story 0)" },
        { "id": "proceed_with_custom_layout", "label": "Yes — waive and document custom layout in manifest" }
      ]
    }
  ]
}
```

Map `proceed_with_custom_layout` → a waiver entry in `clarity.history` and the scaffold manifest deviation log.

### Example — Waive Plan craftsmanship gate

```json
{
  "questions": [
    {
      "id": "waive_plan_craftsmanship",
      "prompt": "Plan craftsmanship gates are not all pass. Waive and continue to Tasks?",
      "options": [
        { "id": "run_gates", "label": "No — run remaining gates" },
        { "id": "waive", "label": "Yes — waive with documented reason" }
      ]
    }
  ]
}
```

## After the user answers

1. Map `option.id` to canonical `state.json`, `policies.yaml`, or the named evidence artifact; never invent removed `context.*` fields.
2. If `save_qa_log` is true, append question + chosen label to `.adlc5/{feature}/qa-log.md`.
3. Proceed only after a form response — **do not** assume defaults unless the skill defines an explicit default when the user skips.

## Stage and step guides

Stage/step guides may list discovery questions as **interview content**. For each question that offers **finite choices**, convert to AskQuestion before proceeding. For open discovery, use chat; when the guide says "ask the user to choose X or Y", use AskQuestion.

## Skills that MUST reference this guide

- [skills/adlc5/SKILL.md](../../skills/adlc5/SKILL.md)
- [skills/adlc5-plan/SKILL.md](../../skills/plan/SKILL.md)
- [adlc5-specify](../../skills/specify/SKILL.md), [adlc5-plan](../../skills/plan/SKILL.md), [adlc5-tasks](../../skills/tasks/SKILL.md), [adlc5-implement](../../skills/implement/SKILL.md)
- Pipeline: [discover](../../skills/discover/SKILL.md), [prt](../../skills/prt/SKILL.md), [qa](../../skills/qa/SKILL.md) when invoked from ADLC5

## Anti-patterns (do not do this)

```markdown
Would you like to enable Auto Mode?
1. Yes - Auto Mode
2. No - Manual Mode
Reply with 1 or 2.
```

```markdown
Phase 2 complete. Ready for Phase 3? (yes/no)
```

Use structured Q&A (AskQuestion on Cursor) instead.

## Non-Cursor fallback template

When no Q&A form tool exists, present:

```markdown
**[Question title]**

1. **{id}** — {label}
2. **{id}** — {label}
3. **{id}** — {label}

Reply with the option id (e.g. `yes`, `auto`, `revise`).
```

Map the user’s reply to the same ids used in `state.json` updates.
