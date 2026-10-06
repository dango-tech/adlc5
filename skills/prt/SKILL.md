---
name: prt
description: PRT - Product Requirements Tracker + UX Ideation + Epic Breakdown - Guides from feature idea through structured product requirements, UX prototype specification, and Jira-ready epic decomposition, with optional handoff to ADLC5 for implementation. Designed for PMs, designers, and anyone with an idea.
author: ADLC5 Contributors
---

# PRT — Product Requirements Tracker + UX Ideation + Epic Breakdown Skill

## Intent

This skill guides the creation of structured Product Requirements Trackers, UX ideation artifacts, and Jira-ready epic breakdowns, enabling "upstream" front-loading before engineering picks up a feature. It is designed for Product Managers, designers, and stakeholders — not just engineers.

**User invokes:** `@prt for [feature]`

**Agent guides through:**
1. **Phase 0: Intake** — Structured interview or existing document import to gather all context before generation *(skippable if input is already detailed)*
2. **Phase 1A: PRT Draft** — Generate a PRT from intake data (Full: 10-section, or Lite: 4-section)
3. **Phase 1B: PRT Review** — Section-by-section review with user, refine flagged sections, quality check *(Full PRT only — skipped for Lite)*
4. **Phase 2: UX Ideation** — Map requirements to design system components, define user journeys, produce framework-specific prototype spec (UI-facing features only)
5. **Phase 3: Epic Breakdown** — Decompose the PRT into independently deliverable, Jira-ready epics with minimal cross-epic dependencies and standalone user value *(optional — skipped if user declines)*

**Optional handoff:** After the final phase, the agent offers to initialize ADLC5 delivery by placing the PRT as context for Phase 1A (Discovery), skipping questions the PRT already answered.

When used under `@adlc5`, **do not start** until `.adlc5/{feature}/state.json` has `git.status` of `completed` or `waived` ([git-isolation.md](../../core/guides/git-isolation.md)). On complete, update `.adlc5/{feature}/memory/summaries/spec.md` and INDEX per [core/guides/working-memory.md](../../core/guides/working-memory.md).

### Model recommendation (first invocation)

```
Recommended model tier: balanced (PRT + UX + epic breakdown).
See skills/adlc5/guides/model-matrix.md and config.yaml model_profiles.
```

## Workspace Setup

### On First Invocation

When `@prt` is invoked, **ALWAYS**:

1. **Extract feature name** from user's request (convert to kebab-case), or ask for one during intake
2. **Check for state file:** Read `{workspace}/.prt/{feature-name}/state.json`
3. **If state file doesn't exist:**
   - Create `.prt/{feature-name}/` directory in workspace
   - Create initial `state.json` with `current_phase: "0"`
   - Start Phase 0 (Intake) — guided interview or document import
   - After intake completes, ask preferences (see [Initial Preferences Setup](#initial-preferences-setup))
   - Then proceed to Phase 1A
4. **If state file exists:**
   - Read current phase and resume from there
   - Load context (feature name, intake data, ui_facing, etc.)

### Initial Preferences Setup

**After Phase 0 (Intake) completes, before starting Phase 1A, collect preferences via AskQuestion** (Cursor Q&A form). See [core/guides/askquestion-convention.md](../../core/guides/askquestion-convention.md). **Do not** use numbered chat lists.

Use **1–2 AskQuestion calls** (batch related questions):

| Question id | When | Maps to | Options (ids) |
|-------------|------|---------|---------------|
| `prt_depth` | Always first | `context.prt_depth` | `full` / `lite` |
| `qa_log` | Always | `context.save_qa_log` | `yes` / `no` |
| `ui_facing` | Always | `context.ui_facing` | `yes` / `no` |
| `framework` | If `ui_facing` yes | `context.framework` | `angular` / `react` / `vue` / `other` / `agnostic` |
| `generate_epics` | Always | `context.generate_epics` | `yes` / `no` |

**PRT Depth behavior:**
- `full` → Full 10-section PRT with Phase 1A (draft) + Phase 1B (section-by-section review). Follows `templates/prt-template.md`.
- `lite` → Concise 4-section PRT generated in a single pass. Follows `templates/prt-lite-template.md`. Skips Phase 1B (no review cycle — user approves via **AskQuestion**). Phase 2 (UX Ideation) is still available if `ui_facing` is true.

If `save_qa_log` is `true`, create and maintain `qa-log.md` throughout the process.
If `save_qa_log` is `false`, skip all Q&A logging.

Store all preferences in state:
```json
{
  "context": {
    "prt_depth": "full",
    "save_qa_log": true,
    "ui_facing": true,
    "framework": "angular",
    "generate_epics": true
  }
}
```

**Framework behavior:**
- `angular` → Phase 2 produces Angular standalone component stubs with `CoreUIModule` imports, `.npmrc`, `angular.json` styles
- `react` → Phase 2 produces React functional component stubs with hooks; references design system class names and tokens
- `vue` → Phase 2 produces Vue 3 Composition API SFC stubs; references design system class names and tokens
- `other` → Phase 2 produces pseudo-code stubs showing component structure, data bindings, and event handlers
- `framework-agnostic` → Phase 2 skips code stubs entirely; outputs component inventory, screen inventory, user journeys, and TypeScript mock data interfaces only

### State File Schema

The agent MUST create and maintain this file at `{workspace}/.prt/{feature-name}/state.json`:

```json
{
  "feature_name": "string (kebab-case)",
  "current_phase": "0",
  "phase_status": {
    "intake": "not_started|in_progress|completed|skipped",
    "prt_draft": "not_started|in_progress|completed",
    "prt_review": "not_started|in_progress|completed",
    "ux_ideation": "not_started|in_progress|completed|skipped",
    "epic_breakdown": "not_started|in_progress|completed|skipped"
  },
  "intake": {
    "entry_point": "interview|import|direct",
    "status": "not_started|in_progress|completed",
    "scope_type": null,
    "problem_statement": null,
    "users": [],
    "stakeholders": [],
    "business_goals": [],
    "in_scope": [],
    "out_of_scope": [],
    "additional_context": null,
    "source_document": null,
    "gaps_identified": [],
    "completed_at": null
  },
  "artifacts": {
    "prt": ".prt/{feature-name}/prt.md",
    "ux_ideation": ".prt/{feature-name}/ux-ideation.md",
    "epic_breakdown": ".prt/{feature-name}/epic-breakdown.md",
    "qa_log": ".prt/{feature-name}/qa-log.md"
  },
  "context": {
    "prt_depth": "full|lite",
    "save_qa_log": true,
    "ui_facing": true,
    "framework": "angular",
    "generate_epics": true
  },
  "rework_history": [],
  "delivery_handoff": {
    "offered": false,
    "accepted": false,
    "delivery_path": null
  },
  "last_updated": "ISO8601 timestamp"
}
```

### Workspace Artifact Structure

All generated files go in the **user's workspace** (NOT in the skills directory):

```
{workspace}/
├── .prt/
│   └── {feature-name}/
│       ├── state.json          # State tracking (agent creates this)
│       ├── qa-log.md           # OPTIONAL: Q&A log (only if user opts in)
│       ├── prt.md              # Phase 1 output: Product Requirements Tracker
│       ├── ux-ideation.md      # Phase 2 output: UX Ideation + Prototype Spec
│       └── epic-breakdown.md   # Phase 3 output: Jira-ready epic decomposition (optional)
└── .adlc5/
    └── {feature-name}/
        ├── prt.md              # OPTIONAL: Copy placed here if ADLC5 handoff accepted
        └── epic-breakdown.md   # OPTIONAL: Copy placed here if ADLC5 handoff accepted AND epics were generated
```

## Phase Flow & State Management

### Phase Detection Logic

**`current_phase` → step ID mapping** (see [phase-registry.md](../../core/guides/phase-registry.md)):

| `current_phase` | Legacy | `phase_status` key | Phase Guide |
|-----------------|--------|-------------------|-------------|
| `prt-0-intake` | `0` | `intake` | `phases/00-intake.md` |
| `prt-1-requirements-draft` | `1a` | `prt_draft` | `phases/01-prt.md` |
| `prt-2-requirements-review` | `1b` | `prt_review` | `phases/01-prt.md` |
| `prt-3-ux-ideation` | `2` | `ux_ideation` | `phases/02-ux-ideation.md` |
| `prt-4-epic-breakdown` | `3` | `epic_breakdown` | `phases/03-epic-breakdown.md` |
| `completed` | — | — | Feature complete |
| *(rework)* | — | — | `phases/rework.md` |

Normalize legacy IDs on read; write new IDs only.

```
1. Extract feature name from user's request (convert to kebab-case)
2. Read {workspace}/.prt/{feature-name}/state.json
3. If file doesn't exist:
   → Create .prt/{feature-name}/ directory
   → Create state.json with current_phase: "0"
   → Start Phase 0 (Intake)
   → After intake: ask preferences (PRT depth, Q&A log, UI-facing, framework)
   → Then start Phase 1A
4. If file exists:
   → Read current_phase field
   → If "completed": Announce feature is done, ask if user wants to revisit or start a new feature
   → Otherwise: Resume from that phase, load context for continuity
```

### Phase Transitions

**CRITICAL: Never auto-advance phases. Always ask user for confirmation.**

After completing work in a phase:
1. Save the artifact to workspace
2. Update state.json with completed status
3. **AskQuestion:** "Phase [N] complete. Ready to move to Phase [N+1]?" — Yes / Revise / Pause ([convention](../../core/guides/askquestion-convention.md))
4. If yes → Update state.json current_phase, start next phase
5. If no → Keep in current phase for refinements

**Note on Phase 0 → 1A:** After intake completes and preferences are collected, the transition to Phase 1A is automatic. The agent uses the intake data to generate the PRT in a single pass. If Phase 0 is skipped (detailed input provided upfront), state transitions directly from `"0"` to `"1a"` with `intake` status set to `"skipped"`.

**Note on Phase 1A → 1B (Full PRT only):** This transition is automatic (no user confirmation needed). After the draft PRT is generated and saved, the agent immediately presents the section-by-section summary for review. The user confirmation point is at the end of Phase 1B, before advancing to Phase 2.

**Note on PRT Lite:** When `prt_depth` is `lite`, Phase 1B is skipped entirely. The agent generates the concise 4-section PRT in Phase 1A, saves it, and asks the user to approve directly. State transitions from `"1a"` straight to `"2"` (or `"3"` if `ui_facing` is false and `generate_epics` is true, or `"completed"` if both are false/skipped).

**Note on Phase 2 → 3:** After Phase 2 (UX Ideation) completes, if `generate_epics` is `true`, **AskQuestion** before Phase 3. If `generate_epics` is `false`, skip Phase 3. If `ui_facing` is `false`, Phase 3 follows directly after Phase 1.

### ADLC5 Delivery Handoff

After the final phase completes (Phase 3 if `generate_epics` is true, Phase 2 if `ui_facing` is true but `generate_epics` is false, or Phase 1 if both are false):

1. **AskQuestion** — ADLC5 handoff (`yes` / `no` manual)
2. If accepted:
   - Create `.adlc5/{feature-name}/prt.md` as a copy of the PRT
   - If epic breakdown was generated (`generate_epics` is true and `epic_breakdown` status is `completed`): also copy `.prt/{feature-name}/epic-breakdown.md` to `.adlc5/{feature-name}/epic-breakdown.md`
3. Update `delivery_handoff` in state.json
4. Announce (adjust based on what was copied):
   - If epic breakdown was included: "PRT and epic breakdown copied to .adlc5/{feature-name}/. When you're ready, invoke @adlc5-plan for {feature-name} and it will load them as context."
   - If PRT only: "PRT copied to .adlc5/{feature-name}/prt.md. When you're ready, invoke @adlc5-plan for {feature-name} and it will load the PRT as context."

### Team Consumption Modes

The PRT output is designed to serve three types of teams:

| Cohort | Description | How the PRT Serves Them |
|--------|-------------|------------------------|
| **Legacy teams** | Not using Cursor; consume PRT as a standard document | The `.prt/{feature-name}/prt.md` file is standalone Markdown — readable in any editor, Confluence, GitHub, or wiki. No Cursor-specific syntax or tooling required. |
| **AI-assisted teams** | Using Cursor + PRT skill for the full workflow | Full Phase 0 → 1 → 2 → 3 → ADLC5 handoff pipeline with state tracking and session continuity. |
| **Cross-cutting teams** | Working across both environments | Import existing PRTs/epics via Phase 0 Path B; export the PRT and epic breakdown as standalone Markdown for offline teams; use ADLC5 handoff for AI-assisted engineering. |

**After all phases complete, AskQuestion for export:**

- prompt: "How would you like to share the PRT?"
- options: `keep` (workspace default) / `export_root` (copy to project root) / `export_all` (prt + ux + epics)

The exported files are plain Markdown with no Cursor-specific dependencies — they work in Confluence, GitHub wikis, Jira, email, or any Markdown renderer.

**Importing existing PRTs/epics:** Phase 0 Path B accepts any written requirements material (PRDs, PRTs, capability docs, epic descriptions, tech specs, meeting notes). The agent extracts structured data and maps it to PRT sections, bridging the gap between legacy artifacts and the structured PRT format.

## Phase Reference Guides

The agent should read these files from the skills directory for detailed methodology:

- **Phase 0 (Intake):** Read `phases/00-intake.md` — Guided interview sequence, document import flow, intake data schema
- **Phase 1 (PRT):** Read `phases/01-prt.md` — PRT draft generation (1A), section-by-section review (1B), prioritization heuristics, quality checklist
- **Phase 1 Agent Instructions:** Read `guides/prt-agent-instructions.md` — Persona, tone, behavioral rules, and clarifying question bank for PRT generation
- **Phase 2:** Read `phases/02-ux-ideation.md` — UX ideation, component mapping, framework-specific prototype spec (UI-facing only)
- **Phase 3:** Read `phases/03-epic-breakdown.md` — Epic decomposition, vertical slicing, dependency mapping, Jira-ready output
- **Rework:** Read `phases/rework.md` — Structured rework process, origin tracing, cascade rules, preference changes (cross-cutting, not a numbered phase)
- **CORE UI Reference:** Read `guides/core-ui-reference.md` — Package info, module variants, component catalog reference
- **PRT Template (Full):** Read `templates/prt-template.md` — Full 10-section PRT template
- **PRT Template (Lite):** Read `templates/prt-lite-template.md` — Concise 4-section PRT template for small features
- **Epic Breakdown Template:** Read `templates/epic-breakdown-template.md` — Jira-ready epic decomposition template

## Resuming Work

If user invokes `@prt` in a workspace with existing state:

1. **Extract feature name** from user's request
2. **Read state file:** `{workspace}/.prt/{feature-name}/state.json`
3. **Announce context:** "Resuming PRT for '{feature_name}'. Currently in Phase {N}: {phase_name}."
4. **Load artifacts:** Read relevant files from workspace
5. **Continue from current phase**

**Note:** If user doesn't specify feature name, list available features by scanning the `.prt/` directory:
1. List all subdirectories under `{workspace}/.prt/` (each subdirectory is a feature)
2. For each subdirectory, read `state.json` to get `current_phase` and phase status
3. Present the list to the user:

```
User: "@prt"
Agent: "Found existing PRT projects in this workspace:
        1. invoice-approval (Phase 0: Intake - in progress)
        2. vendor-dashboard (Phase 1B: PRT Review)
        3. campaign-dashboard (Phase 2: UX Ideation)

        Which feature would you like to continue with, or would you like to start a new one?"
```

If the `.prt/` directory doesn't exist or is empty, treat this as a new invocation and start Phase 0.

## Agent Instructions Summary

### On Every Invocation

1. **Extract feature name** from user's request (or list available if not specified)
2. **Read workspace state:** `{workspace}/.prt/{feature-name}/state.json`
3. **Determine phase:** Extract current_phase or start at 0
4. **Load agent instructions:** Read `guides/prt-agent-instructions.md` for persona, tone, and behavioral rules
5. **Load phase guide:** Read appropriate `phases/{N}-*.md` file. If user requests changes to a completed artifact, read `phases/rework.md` instead.
6. **Load workspace artifacts:** Read relevant intake data, prt, ux-ideation, epic-breakdown files
7. **Execute phase:** Follow methodology from phase guide
8. **Save artifacts:** Write to `{workspace}/.prt/{feature-name}/...`
9. **Update Q&A log (if enabled):** If `context.save_qa_log` is `true`, append Q&A to `qa-log.md`
10. **Update state:** Write updated `{workspace}/.prt/{feature-name}/state.json`
11. **Ask for confirmation:** Before advancing to next phase (except 0 → 1A and 1A → 1B which are automatic)

### Never Do

- ❌ Auto-advance phases without user confirmation (except 0 → 1A and 1A → 1B)
- ❌ Skip state updates
- ❌ Assume phase without reading state
- ❌ Create artifacts without proper workspace paths
- ❌ Forget to load context when resuming
- ❌ Skip Phase 0 (Intake) when the user's input is vague — run the interview or import flow
- ❌ Generate a full PRT from a thin description without structured intake data
- ❌ Reference non-CORE UI components for Epsilon UI work
- ❌ Skip the ADLC5 handoff offer after completion
- ❌ Skip the section-by-section review in Phase 1B — always present the summary table
- ❌ Mark all requirements as Must — if >60% are Must, reconsider priorities
- ❌ Slice epics horizontally by technical layer (all APIs, then all UI) — always slice vertically by user capability
- ❌ Leave orphaned stories or requirements that don't appear in any epic
- ❌ Create circular dependencies between epics
- ❌ Make untracked changes to completed artifacts — all rework must go through `phases/rework.md` with state tracking
- ❌ Fix downstream symptoms without checking upstream root cause (e.g., rearranging epics when stories aren't independent)
- ❌ Regenerate entire artifacts when only one section changed — minimal blast radius

### Always Do

- ✅ Extract feature name first
- ✅ Read state from `.prt/{feature-name}/state.json`
- ✅ Run Phase 0 (Intake) for new features — guided interview or document import
- ✅ Load `guides/prt-agent-instructions.md` for persona and behavioral rules
- ✅ Save all artifacts to workspace
- ✅ Update state after significant actions
- ✅ Log all Q&A exchanges to `qa-log.md` immediately (if enabled)
- ✅ **AskQuestion** before phase transitions (except 0 → 1A and 1A → 1B)
- ✅ Load phase guides for detailed methodology
- ✅ Use workspace-relative paths for all artifacts
- ✅ Reference CORE UI components from `guides/core-ui-reference.md` for any UI-related sections
- ✅ Use intake data from Phase 0 as source material for Phase 1A — skip redundant clarifying questions
- ✅ Present section-by-section summary in Phase 1B and let user flag sections for revision
- ✅ Use prioritization heuristics from `phases/01-prt.md` when assigning Must/Should/Could/Won't
- ✅ Offer ADLC5 handoff after all phases complete
- ✅ In Phase 2: Check `context.framework` and produce framework-appropriate prototype spec
- ✅ In Phase 3: Slice epics vertically — each epic delivers end-to-end user value, not a technical layer
- ✅ In Phase 3: Verify every PRT story and requirement maps to exactly one epic (traceability matrix)
- ✅ In Phase 3: Minimize cross-epic dependencies; flag dependency chain depth > 3 as a smell
- ✅ Accept imported PRTs, PRDs, epics, or other existing requirements documents via Phase 0 Path B
- ✅ When user requests changes to completed artifacts, load `phases/rework.md` and follow the structured rework process
- ✅ Trace rework to the origin phase — fix upstream first, then cascade forward
- ✅ Track every rework cycle in state.json `rework_history` with a unique ID
- ✅ Add revision history to modified artifacts so future readers understand what changed and why

## Quality Standards

Every phase output must meet these standards:
- **PRT (Full):** Complete all 10 sections — no TBD without explanation, no skipped sections
- **PRT (Lite):** Complete all 4 sections — problem statement, scope, user stories, and requirements with acceptance criteria
- **User Stories:** Written in "As a [role], I want [goal] so that [benefit]" format with priorities
- **Functional Requirements:** Use Must/Should/Could/Won't prioritization with heuristics from Phase 1 guide; no more than 60% of requirements should be Must
- **UI/UX:** ALWAYS reference CORE UI components — never generic or made-up component names
- **UX Ideation:** Testable user journeys; prototype spec matches the `framework` preference (Angular/React/Vue/other/agnostic)
- **Epic Breakdown:** Every PRT story/requirement in exactly one epic; no circular dependencies; each epic delivers standalone user value; dependency chain depth ≤ 3
- **Rework:** Origin phase identified (not symptom phase); changes cascaded forward to all downstream artifacts; revision history annotated; rework tracked in state.json; consistency check passed
- **Tone:** Professional, neutral, fact-based — like a senior PM writing for engineering + stakeholders
