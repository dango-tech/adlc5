---
name: intake
description: Phase 0 - Intake. Structured interview or document import that gathers all context before PRT generation begins. Ensures the agent has enough information to produce a high-quality PRT without back-and-forth during Phase 1.
---

# Phase 0: Intake

## Purpose

Gather all the context the agent needs to produce a high-quality PRT — **before** generation starts. This replaces the ad-hoc "clarify if vague" pattern with a structured process that works for any starting point: a rough idea, a detailed description, or an existing document.

## Why This Phase Exists

Without structured intake, the agent either:
- Generates a PRT from sparse input and fills it with assumptions, or
- Interrupts the user repeatedly during Phase 1A with clarifying questions

Phase 0 front-loads all discovery so Phase 1A can generate in a single pass with high confidence.

## Entry Points

Phase 0 begins by **checking for a BRD**, then presenting a welcome message.

### BRD Detection (Path C Check)

Before presenting the welcome message, check for a BRD from the Ideate skill:

```
Read {workspace}/.prt/{feature-name}/brd.md
```

**If the file exists:** Skip the welcome message and go directly to [Path C: BRD Import](#path-c-brd-import).

**If the file does not exist:** Present the welcome message below.

### Welcome Message (when no BRD is present)

```
"Welcome to the PRT skill. I'll help you create a structured Product Requirements Tracker.

How would you like to get started?

1. Guided interview — I'll walk you through a series of questions to capture your requirements step by step (best when starting from a rough idea)
2. Import existing document — Paste or attach an existing PRD, PRT, epic, spec, or requirements document and I'll extract the key information (best when you already have written material)"
```

Store the choice in state:
```json
{
  "intake": {
    "entry_point": "interview|import|direct|ideate",
    "status": "in_progress"
  }
}
```

---

## Path A: Guided Interview

A structured, step-by-step interview that collects the core inputs for PRT generation. Each step asks one focused question, waits for the answer, then moves to the next.

### Interview Sequence

#### Step 1: Scope Type

```
"What type of work is this?

1. New feature — net-new capability that doesn't exist today
2. Enhancement — improvement to an existing feature or flow
3. Internal tooling — ops tool, admin panel, or internal workflow
4. Integration — connecting two systems or adding a new data source
5. Other (describe briefly)"
```

Store as `intake.scope_type`.

#### Step 2: Feature Name

```
"What should we call this feature? (A short name I'll use for file naming and tracking — e.g., 'invoice-approval', 'campaign-dashboard', 'vendor-onboarding')"
```

If the user already provided a name in the initial `@prt for [feature]` invocation, confirm it:
```
"I'll use '{feature-name}' as the project name. Sound right, or would you prefer a different name?"
```

Store as `feature_name` (convert to kebab-case).

#### Step 3: Core Problem

```
"What problem does this solve? Describe in 2-3 sentences:
- What is broken, slow, or missing today?
- What do users currently have to do as a workaround (if anything)?"
```

Store as `intake.problem_statement`.

#### Step 4: Stakeholders & Users

```
"Who are the key people involved?

- **Primary users:** Who will use this feature day-to-day? (role names, e.g., 'Finance Ops Analyst', 'Campaign Manager')
- **Stakeholders:** Who needs to sign off or cares about the outcome? (e.g., 'VP of Finance', 'Product Lead')
- **Affected teams:** Any other teams impacted? (e.g., 'Engineering', 'QA', 'Design')"
```

Store as `intake.users` and `intake.stakeholders`.

#### Step 5: Business Goals

```
"What are the business goals or outcomes you're hoping for?

Examples:
- 'Reduce invoice processing time from 8 min to under 2 min'
- 'Eliminate manual data entry for campaign setup'
- 'Enable self-service vendor onboarding without ops team involvement'

List 1-3 goals. It's OK if they're approximate — we'll refine them in the PRT."
```

Store as `intake.business_goals`.

#### Step 6: Scope Boundaries

```
"Let's define the boundaries for this phase:

- **Must include:** What are the 2-4 things that absolutely must be in the first release?
- **Explicitly excluded:** What should we NOT build in this phase? (Even if it comes up later — naming exclusions now prevents scope creep)"
```

Store as `intake.in_scope` and `intake.out_of_scope`.

#### Step 7: Additional Context (optional)

```
"Anything else I should know? (Optional — skip if nothing comes to mind)

Examples of useful context:
- Existing API endpoints or data sources this connects to
- Compliance or regulatory constraints
- Timeline or deadline pressures
- Prior art — similar features in other Epsilon apps
- Links to Figma mockups, Jira epics, or Confluence pages"
```

Store as `intake.additional_context`.

#### Step 8: Review Summary

After collecting all answers, present a summary:

```
"Here's what I've captured:

**Feature:** {feature_name}
**Type:** {scope_type}
**Problem:** {problem_statement — 1-2 sentences}
**Primary users:** {users}
**Business goals:**
- {goal 1}
- {goal 2}
**In scope:** {in_scope items}
**Out of scope:** {out_of_scope items}
**Additional context:** {additional_context or 'None'}

Does this look right? I'll use this as the foundation for generating your PRT.

1. Looks good — proceed to preferences and PRT generation
2. I need to change something — (tell me what to update)"
```

If the user wants changes, update the relevant fields and re-present the summary.

### After Interview: Transition

Once the user approves the summary:
1. Save intake data to state.json under `intake` object
2. Mark `intake.status: "completed"`
3. Proceed to Initial Preferences Setup (PRT depth, Q&A logging, UI-facing, framework) — see the "Initial Preferences Setup" section in `SKILL.md`
4. Then proceed to Phase 1A — the agent uses the intake data as its source material instead of asking clarifying questions

---

## Path B: Import Existing Document

For users who already have written requirements — a PRD, PRT, epic, capability doc, spec, or any existing requirements artifact.

### Step 1: Receive the Document

```
"Paste or share your existing document below. I can work with:

- Product Requirements Documents (PRDs)
- PRTs / capability documents / epic descriptions
- Technical specs or design docs
- Jira epic/story descriptions
- Meeting notes or stakeholder emails
- Any other written requirements material

Paste the content directly, or tell me the file path if it's already in this workspace."
```

### Step 2: Extract & Summarize

After receiving the document, the agent extracts key information and maps it to PRT inputs:

```
"I've read your document. Here's what I extracted:

**Feature name:** {extracted or suggested}
**Problem statement:** {extracted}
**Users/personas:** {extracted}
**Business goals:** {extracted}
**In scope:** {extracted}
**Out of scope:** {extracted or '[NOT FOUND — I'll ask you]'}
**Additional context:** {anything else relevant}

**Gaps I noticed:**
- {List any PRT-critical information not found in the source document}
- {e.g., 'No success metrics mentioned', 'Scope exclusions not defined', 'User personas not identified'}

For the gaps, I'll either ask you directly or flag them as [ASSUMPTION] in the PRT.

Does this extraction look right?

1. Looks good — proceed to preferences and PRT generation
2. I need to correct something — (tell me what's wrong)
3. Fill the gaps now — ask me about the missing items"
```

### Step 3: Fill Gaps (if user chooses option 3)

For each gap identified, ask a targeted question:
```
"I noticed the source document doesn't mention [gap]. Quick question:
[Targeted question about the gap]"
```

Ask gaps one at a time, max 3 per message.

### Step 4: Confirm & Transition

Once the user approves the extraction:
1. Save extracted data to state.json under `intake` object, with `entry_point: "import"` and `source_document: "inline|filepath"`
2. Mark `intake.status: "completed"`
3. Proceed to Initial Preferences Setup (PRT depth, Q&A logging, UI-facing, framework) — see the "Initial Preferences Setup" section in `SKILL.md`
4. Then proceed to Phase 1A — the agent uses extracted data as source material

---

## Path C: BRD Import

For users who have completed the `@ideate` skill and have a BRD at `.prt/{feature-name}/brd.md`. This path auto-populates intake fields from the BRD and skips redundant questions.

### Step 1: Announce BRD Found

```
"I found a BRD at .prt/{feature-name}/brd.md from the Ideate skill.
I'll use it to populate the intake fields — you won't need to answer questions already covered there.

Let me extract the relevant information..."
```

### Step 2: Extract and Map to Intake Fields

Read the BRD and map each section to PRT intake fields:

| BRD Section | PRT Intake Field |
|------------------------|-----------------|
| Problem Statement | `intake.problem_statement` |
| Who Is Affected → Primary users | `intake.users` |
| Who Is Affected → Secondary stakeholders | `intake.stakeholders` |
| The Opportunity + Success Criteria | `intake.business_goals` |
| Scope Sketch → MVP (in scope) | `intake.in_scope` |
| Scope Sketch → Explicitly excluded | `intake.out_of_scope` |
| Constraints | `intake.additional_context` |
| Prior Art and Context | append to `intake.additional_context` |
| Open Questions | `intake.gaps_identified` |

Also store:
```json
{
  "intake": {
    "entry_point": "ideate",
    "source_document": ".prt/{feature-name}/brd.md"
  }
}
```

### Step 3: Present Extracted Summary

```
"Here's what I extracted from the BRD:

**Feature:** {feature_name}
**Problem:** {problem_statement — 1-2 sentences}
**Primary users:** {users}
**Business goals / success criteria:**
- {goal/criterion 1}
- {goal/criterion 2}
**In scope:** {in_scope items}
**Out of scope:** {out_of_scope items}
**Constraints:** {constraints or 'None identified'}

**Open questions from the ideation session:**
{gaps_identified — as bullet list, or 'None'}

Does this look right? I'll use this as the foundation for generating your PRT.
These open questions will be flagged as [ASSUMPTION] items in the PRT.

1. Looks good — proceed to preferences and PRT generation
2. I need to change something — (tell me what to update)
3. Fill the open questions now — ask me about the unresolved items"
```

### Step 4: Fill Open Questions (if user chooses option 3)

For each open question from the BRD, ask a targeted question:
```
"The ideation session left this unresolved: '{open question}'.

{targeted follow-up question to resolve it}"
```

Ask questions one at a time, max 3 per message.

### Step 5: Confirm and Transition

Once the user approves:
1. Save extracted data to state.json under `intake` object
2. Mark `intake.status: "completed"` and `intake.completed_at` with current timestamp
3. Proceed to Initial Preferences Setup — see the "Initial Preferences Setup" section in `SKILL.md`
4. Then proceed to Phase 1A — intake data from the BRD serves as source material

**Note:** The BRD's "Risks Acknowledged" section should be referenced in PRT Section 10 (Risks/Dependencies). The agent should proactively include these risks rather than waiting for the user to mention them.

---

The intake object stored in state.json:

```json
{
  "intake": {
    "entry_point": "interview|import|direct|ideate",
    "status": "not_started|in_progress|completed",
    "scope_type": "new_feature|enhancement|internal_tooling|integration|other",
    "problem_statement": "string",
    "users": ["string"],
    "stakeholders": ["string"],
    "business_goals": ["string"],
    "in_scope": ["string"],
    "out_of_scope": ["string"],
    "additional_context": "string|null",
    "source_document": "inline|filepath|null",
    "gaps_identified": ["string"],
    "completed_at": "ISO8601 timestamp"
  }
}
```

---

## How Phase 1A Uses Intake Data

When Phase 1A starts and `intake.status` is `completed`, the agent should:

1. **Load intake data from state.json and skip clarifying questions** — all discovery has already been completed in Phase 0 (see Phase 1A Step 1: Load Intake Data in `phases/01-prt.md`)
2. **Map intake fields to PRT sections:**

| Intake Field | PRT Section (Full) | PRT Section (Lite) |
|-------------|-------------------|-------------------|
| `problem_statement` | Section 2: Problem Statement | Section 1: Problem & Context |
| `users` | Section 2: User personas | Section 1: Who is affected |
| `business_goals` | Section 1: Business Objectives | Section 1: Problem & Context |
| `in_scope` | Section 3: In Scope | Section 2: In Scope |
| `out_of_scope` | Section 3: Out of Scope | Section 2: Out of Scope |
| `stakeholders` | Section 1: Stakeholders, Section 9: Sign-off | — |
| `scope_type` | Informs tone and depth across all sections | Informs tone |
| `additional_context` | Distributed across relevant sections | Section 4: Key constraints |
| `source_document` | Referenced in Appendix | — |

3. **Generate the PRT** in a single pass — the intake provides enough material that no additional clarifying questions should be needed

---

## Skipping Phase 0

Phase 0 is **not mandatory**. If the user provides a highly detailed description in their initial `@prt for [feature]` invocation (covers problem, users, scope, and goals), the agent may:

1. Assess that all 4 intake criteria are met (problem clear, users identified, scope bounded, goals stated)
2. Skip Phase 0 entirely
3. Set `intake.status: "completed"` with `entry_point: "direct"` and populate intake fields from the description
4. Proceed directly to Initial Preferences Setup → Phase 1A

The agent should announce: "Your description is detailed enough to start generating. Proceeding directly to PRT generation."

If the description is thin, the agent **must** run Phase 0.

---

## Definition of Done

Phase 0 is complete when:
- [ ] Entry point chosen (interview or import)
- [ ] All required fields populated: problem_statement, users, business_goals, in_scope, out_of_scope
- [ ] Summary presented to user and approved
- [ ] Intake data saved to state.json
- [ ] `intake.status` set to `"completed"`
