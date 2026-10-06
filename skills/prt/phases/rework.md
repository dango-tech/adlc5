---
name: rework
description: Rework & Iteration (cross-cutting, not a numbered phase). Guides structured rework when feedback, changed requirements, or new insights require revisiting previous PRT phase artifacts. Routes changes to the correct origin phase and cascades updates downstream.
---

# Rework & Iteration

## Purpose

Provide a structured process for handling rework — when stakeholder feedback, changed requirements, new context, or downstream discoveries require revisiting previous phase artifacts. Without this, rework is ad-hoc and either too aggressive (redo everything) or too timid (patch symptoms, not causes).

**This is not a sequential phase.** Rework can be triggered at any point and sends you back to the correct origin phase with targeted changes, then cascades updates forward through affected downstream artifacts.

## When to Use This Guide

The agent should read this guide when any of the following occur:

- User says "change", "rework", "redo", "fix", "update", "revise" about a completed artifact
- Stakeholder feedback invalidates previous assumptions in the PRT
- UX ideation reveals a gap or flaw in the PRT (missing story, wrong scope, bad requirement)
- Epic breakdown reveals that stories aren't independent enough or scope needs adjustment
- New requirements emerge mid-process that affect completed phases
- Design team feedback on UX ideation requires PRT changes
- User wants to change preferences (e.g., switch from Lite to Full, add UX ideation after initially declining)
- ADLC5 implementation feedback traces back to a PRT issue

## Rework Principles

### 1. Fix the Root, Not the Symptom

```
❌ BAD: Epic breakdown has too many dependencies → rearrange epics
   (But the stories in the PRT aren't independent, so any grouping will have dependencies)

✅ GOOD: Epic breakdown has too many dependencies → trace to PRT → revise stories
         to be more independent → regenerate epic breakdown
   (Root cause fixed, artifacts stay consistent)
```

### 2. Minimal Blast Radius

```
Don't redo everything. Only update what actually changed.

❌ BAD: "One user story was wrong, let me regenerate the entire PRT"
✅ GOOD: "One user story was wrong, let me update Section 4 in prt.md,
         check if it affects the UX ideation journey, and update the
         epic breakdown traceability"
```

### 3. Cascade Forward, Never Skip

```
If you change Phase 0 (Intake), check Phase 1, 2, 3.
If you change Phase 1 (PRT), check Phase 2, 3.
If you change Phase 2 (UX Ideation), check Phase 3.
If you change Phase 3 (Epic Breakdown) only, no cascade needed.

Never update a downstream artifact without checking if its upstream is still valid.
```

### 4. Track Everything

```
Every rework cycle must be tracked in state.json.
This creates an audit trail and prevents rework loops.
```

## Rework Classification

### Step 1: Identify the Trigger

Before making any changes, classify what happened:

| Trigger | Description | Example |
|---------|-------------|---------|
| `feedback-prt` | Stakeholder/reviewer wants PRT changes | "We need to add a new user persona" |
| `feedback-scope` | Scope needs adjustment | "Bulk approval should be in scope for Phase 1" |
| `feedback-stories` | User stories need revision | "These stories aren't independent enough for separate epics" |
| `feedback-requirements` | Functional requirements need changes | "FR-003 acceptance criteria is untestable" |
| `feedback-ux` | UX ideation needs revision | "The journey doesn't account for error states" |
| `feedback-epics` | Epic grouping needs adjustment | "These two epics should be merged — they share too much" |
| `gap-discovered` | Downstream phase reveals missing upstream content | "UX ideation found we need a story for the empty state" |
| `requirements-change` | New or changed business requirements | "We also need manager approval for invoices over $10K" |
| `preference-change` | User wants to change a skill preference | "Actually, make this a Full PRT instead of Lite" |
| `delivery-traceback` | ADLC5 implementation reveals PRT issue | "The spec is correct per PRT, but the PRT requirement was wrong" |

### Step 2: Determine the Origin Phase

**Critical: Find where the actual change needs to happen, not where the symptom appeared.**

```
Symptom in Phase 3 (Epic Breakdown)?
  → Is the epic grouping wrong but stories are fine?     → Origin: Phase 3
  → Are the stories not independent enough?              → Origin: Phase 1 (PRT Section 4)
  → Is the scope wrong?                                  → Origin: Phase 1 (PRT Section 3)

Symptom in Phase 2 (UX Ideation)?
  → Is the component mapping wrong but PRT is right?     → Origin: Phase 2
  → Is the journey wrong because a story is missing?     → Origin: Phase 1 (PRT Section 4)
  → Is the requirement wrong?                            → Origin: Phase 1 (PRT Section 5)

Symptom in Phase 1 (PRT)?
  → Is the PRT section wrong but intake data is right?   → Origin: Phase 1
  → Was the intake data incomplete or wrong?             → Origin: Phase 0

Ask yourself: "If I fix ONLY this phase, will the problem be fully resolved?"
  → If yes, this is the origin phase
  → If no, go one phase earlier and ask again
```

**Decision Tree:**

```
User reports issue
    │
    ├─ Is this an epic grouping change only? (merge, split, move stories between epics)
    │   └─ YES → Origin: Phase 3 (Epic Breakdown) — regroup, no cascade
    │
    ├─ Is the UX wrong? (bad component, wrong journey, missing screen)
    │   ├─ Is the UX wrong because the PRT requirement is wrong?
    │   │   └─ YES → Origin: Phase 1 (PRT) — fix requirement, cascade to Phase 2 + 3
    │   └─ NO → Origin: Phase 2 (UX Ideation) — fix UX, cascade to Phase 3
    │
    ├─ Is the PRT wrong? (wrong story, bad scope, missing requirement)
    │   ├─ Is the PRT wrong because intake data was wrong/missing?
    │   │   └─ YES → Origin: Phase 0 (Intake) — fix intake, cascade to Phase 1 + 2 + 3
    │   └─ NO → Origin: Phase 1 (PRT) — fix PRT, cascade to Phase 2 + 3
    │
    └─ Is it a preference change? (Lite → Full, add UX, add epics)
        └─ YES → See "Preference Changes" section below
```

### Step 3: Assess the Scope

| Scope | Description | Estimated Effort | Examples |
|-------|-------------|------------------|----------|
| **Cosmetic** | Wording, formatting, typos | Minutes | Fix a story's wording, rename an epic |
| **Targeted** | Single story, single requirement, single screen | < 30 min | Add missing acceptance criterion, fix one journey |
| **Moderate** | Multiple related stories or requirements | 30 min - 2 hours | Add a new persona with 2-3 stories, revise scope boundaries |
| **Significant** | Cross-section PRT changes affecting multiple downstream artifacts | 2-4 hours | Add a new capability to scope, change the data model |
| **Major** | Fundamental scope or approach change | Half day+ | Switch from Lite to Full PRT, add an entirely new user journey |

**For Significant/Major rework, ALWAYS confirm with the user before proceeding:**
```
"This change affects multiple artifacts. Here's what needs to change:
- Phase 1 (PRT): [specific sections affected]
- Phase 2 (UX Ideation): [specific screens/journeys affected]
- Phase 3 (Epic Breakdown): [epics that need regrouping]

Estimated effort: [time]. Should I proceed?"
```

## Rework Process

### Step 1: Document the Rework Request

Before making any changes, create a rework entry:

```markdown
## Rework: [Brief Description]

**Trigger:** [trigger type from classification table]
**Origin Phase:** [0/1/2/3]
**Scope:** [cosmetic/targeted/moderate/significant/major]
**Requested By:** [user/stakeholder/design-team/delivery-traceback]
**Description:** [What needs to change and why]

**Affected Artifacts:**
- [ ] `.prt/{feature}/prt.md` — [what changes: which sections]
- [ ] `.prt/{feature}/ux-ideation.md` — [what changes: which screens/journeys]
- [ ] `.prt/{feature}/epic-breakdown.md` — [what changes: which epics]

**Impact on Downstream:** [None / Phase 2 journey X affected / Epic E2 needs regrouping / etc.]
```

### Step 2: Fix the Origin Phase Artifact

Go to the origin phase and make the targeted change.

**Rules for editing existing artifacts:**

1. **Mark changes clearly** — Add a revision section at the top of the artifact:
```markdown
## Revision History
| Date | Change | Reason | Rework ID |
|------|--------|--------|-----------|
| YYYY-MM-DD | Added FR-005: manager approval for high-value invoices | New business requirement from Finance VP | rework-001 |
```

2. **Don't delete, annotate** — When removing content, explain why:
```markdown
~~**Story 3 (Should):** As a Finance Ops Analyst, I want to export invoices to CSV...~~
**[REMOVED in rework-001]:** Moved to out-of-scope. Will be addressed in Phase 2 of the product roadmap.
```

3. **Preserve context** — Future readers need to understand why things changed

### Step 3: Cascade Forward

After fixing the origin, cascade changes to every downstream phase:

#### Cascade from Phase 0 (Intake)

```
Phase 0 changed (intake data corrected or expanded)
    │
    ├─→ Phase 1 (PRT)
    │   ├─ Do PRT sections need updating with new intake data?
    │   ├─ Are new stories or requirements needed?
    │   ├─ Has the scope changed?
    │   └─ Do success metrics need revising?
    │
    ├─→ Phase 2 (UX Ideation) — if exists
    │   ├─ Do component mappings need updating?
    │   ├─ Do user journeys need revising?
    │   └─ Are new screens needed?
    │
    └─→ Phase 3 (Epic Breakdown) — if exists
        ├─ Do epics need regrouping?
        ├─ Has the traceability matrix changed?
        └─ Do dependencies need reassessing?
```

#### Cascade from Phase 1 (PRT)

```
Phase 1 changed
    │
    ├─→ Phase 2 (UX Ideation) — if exists
    │   ├─ New/changed stories → new/updated journeys needed?
    │   ├─ New/changed requirements → component inventory needs updating?
    │   ├─ Scope change → screens need adding/removing?
    │   └─ Priority changes → journey ordering affected?
    │
    └─→ Phase 3 (Epic Breakdown) — if exists
        ├─ New/changed stories → traceability matrix needs updating
        ├─ Stories added → which epic do they belong to?
        ├─ Stories removed → does any epic become empty or too small?
        ├─ Priority changes → does the MVP epic (E1) need adjusting?
        └─ Scope changes → do dependency arrows change?
```

#### Cascade from Phase 2 (UX Ideation)

```
Phase 2 changed
    │
    └─→ Phase 3 (Epic Breakdown) — if exists
        ├─ Screen changes → do epic boundaries shift? (screens often map to epic boundaries)
        ├─ Journey changes → do story groupings still make sense?
        └─ New custom component needs → does this create a new dependency?
```

#### No Cascade Needed

```
Phase 3 changed (epic regrouping only)
    │
    └─ Regroup epics, update traceability matrix, done
        (No upstream artifacts affected — epic grouping is a downstream-only decision)
```

### Step 4: Verify Consistency

After cascading all changes, verify the entire chain is consistent:

```markdown
### Consistency Check

- [ ] PRT sections are internally consistent (stories match scope, requirements match stories)
- [ ] UX ideation references match current PRT content (journeys cover current stories, components map to current requirements)
- [ ] Epic breakdown covers all current PRT stories and requirements (traceability matrix is complete)
- [ ] No orphaned references (nothing points to deleted/changed content)
- [ ] Priority distribution still passes sanity check (no more than 60% Must)
- [ ] Epic dependencies are still valid after changes
```

### Step 5: Update State

Update `state.json` to track the rework:

```json
{
  "rework_history": [
    {
      "id": "rework-001",
      "trigger": "requirements-change",
      "origin_phase": "1",
      "scope": "moderate",
      "description": "Added manager approval workflow for invoices over $10K",
      "affected_artifacts": [
        ".prt/{feature}/prt.md",
        ".prt/{feature}/ux-ideation.md",
        ".prt/{feature}/epic-breakdown.md"
      ],
      "sections_changed": ["Section 3 (Scope)", "Section 4 (Stories)", "Section 5 (Requirements)"],
      "status": "completed",
      "created_at": "2025-03-01T10:00:00Z",
      "completed_at": "2025-03-01T11:30:00Z"
    }
  ]
}
```

**Rework status values:**
- `identified` — Rework documented, not yet started
- `in_progress` — Actively making changes
- `cascading` — Origin fixed, cascading to downstream artifacts
- `verifying` — Changes complete, running consistency check
- `completed` — All changes made and verified

## Preference Changes

When the user wants to change a preference mid-process, this is a special type of rework:

### Lite → Full PRT

```
1. Set prt_depth to "full" in state.json context
2. Read the existing Lite PRT
3. Expand into the full 10-section template, using Lite content as the base:
   - Lite Section 1 (Problem & Context) → Full Sections 1 + 2
   - Lite Section 2 (Scope) → Full Section 3
   - Lite Section 3 (User Stories) → Full Section 4
   - Lite Section 4 (Requirements) → Full Sections 5 + 6 + 7
   - Generate Sections 8, 9, 10 from context
4. Run Phase 1B (section-by-section review) on the expanded PRT
5. Cascade to Phase 2 and 3 if they exist
```

### Add UX Ideation After Initially Declining

```
1. Set ui_facing to true in state.json context
2. Ask for framework preference
3. Set current_phase to "2"
4. Run Phase 2 normally using the existing PRT
5. If Phase 3 was already completed, cascade (re-run epic breakdown with UX context)
```

### Add Epic Breakdown After Initially Declining

```
1. Set generate_epics to true in state.json context
2. Set current_phase to "3"
3. Run Phase 3 normally using the existing PRT (and UX ideation if available)
```

## Common Rework Scenarios

### Scenario 1: Stakeholder Feedback on PRT

**Trigger:** Product VP says "we need to add audit logging as a Must requirement"

```
1. Classify: requirements-change, Origin: Phase 1 (PRT), Scope: targeted
2. Update PRT:
   - Add FR-XXX to Section 5 (Functional Requirements)
   - Add to Section 7 (Non-Functional) if it's a cross-cutting concern
   - Update Section 3 (Scope) if needed
3. Cascade to Phase 2: Does the audit log need a UI? If yes, add screen/journey
4. Cascade to Phase 3: Add FR-XXX to traceability matrix, assign to an epic
5. Update state.json with rework entry
```

### Scenario 2: UX Ideation Reveals Missing Story

**Trigger:** While mapping journeys, agent discovers there's no story for the "empty state" (what the user sees when there's no data)

```
1. Classify: gap-discovered, Origin: Phase 1 (PRT), Scope: targeted
2. Go back to PRT:
   - Add the missing story to Section 4
   - Add corresponding requirement to Section 5
3. Return to Phase 2: Add the empty state to the screen inventory and journey
4. Cascade to Phase 3: Add story to traceability matrix, assign to the foundation epic (E1)
```

### Scenario 3: Epic Breakdown Reveals Coupled Stories

**Trigger:** During epic breakdown, agent finds that Stories 2 and 5 are so tightly coupled that putting them in different epics creates a circular dependency

```
1. Classify: feedback-stories, determine origin:
   → Can we just group them in the same epic? → Origin: Phase 3 (just regroup)
   → Are the stories fundamentally not independent? → Origin: Phase 1 (rewrite stories)
2. If stories need rewriting:
   - Update Section 4 in PRT to make them more independent
   - Check if acceptance criteria in Section 5 need adjusting
   - Cascade to Phase 2 (journey may need updating)
   - Re-run Phase 3 epic decomposition
3. If just regrouping:
   - Move stories between epics in epic-breakdown.md
   - Update traceability matrix
   - No upstream cascade needed
```

### Scenario 4: ADLC5 Traceback

**Trigger:** During ADLC5 implementation, the engineering team discovers that the PRT requirement FR-002 is ambiguous — "users can filter by status" doesn't specify which statuses exist

```
1. Classify: delivery-traceback, Origin: Phase 1 (PRT), Scope: cosmetic/targeted
2. Update PRT:
   - Clarify FR-002 acceptance criteria with the specific status values
   - Update Section 4 story if needed
3. Cascade to Phase 2: Update component config (e.g., filter bar options)
4. Cascade to Phase 3: No change needed (story didn't change, just got clearer)
5. Communicate back to ADLC5 delivery team: "PRT updated, the statuses are: [list]"
```

### Scenario 5: Complete Scope Pivot

**Trigger:** "We're dropping the approval workflow. This should just be a read-only dashboard."

```
1. Classify: requirements-change, Origin: Phase 1 (PRT), Scope: major
2. STOP: Confirm with user before proceeding
   "This is a major scope change. Here's what would need to change:
    - Phase 1 (PRT): Remove approval stories/requirements, update scope, revise success metrics
    - Phase 2 (UX): Remove approval screens/journeys, simplify component inventory
    - Phase 3 (Epics): Complete regrouping — approval epics removed
    
    Option A: Rework the existing PRT (revise all artifacts)
    Option B: Start a new PRT for the dashboard feature
    Which approach do you prefer?"
3. Based on user choice, either rework in place or create a new feature
```

## Rework Anti-Patterns

❌ **Scorched Earth Rework**
```
"The stakeholder didn't like Section 4, let me regenerate the entire PRT"
→ Only update Section 4. Check if the change cascades to Sections 5/6/7, then Phase 2/3.
```

❌ **Symptom Patching**
```
"The epics have too many dependencies, let me rearrange them"
→ Ask: Are the dependencies because the grouping is wrong, or because the stories
  aren't independent? If stories aren't independent, fix the PRT first.
```

❌ **Invisible Rework**
```
"I'll just quietly fix this section"
→ All rework must be tracked in state.json and annotated in artifacts with revision history.
   Future readers need to understand what changed and why.
```

❌ **Cascading Without Checking**
```
"PRT scope changed, so let me regenerate the entire UX ideation"
→ Check each screen/journey: does this scope change actually affect it?
   Often only 1-2 journeys are affected, not all of them.
```

❌ **Rework Loops**
```
Fix A causes issue B, fix B causes issue C, fix C causes issue A again
→ If you're on rework-003+ for the same area, STOP.
  Step back, re-evaluate. Consider: "Is the scope or approach fundamentally wrong?"
```

❌ **Deferring Rework**
```
"I'll fix the PRT later, let me just update the epic breakdown"
→ Artifacts drift out of sync. Fix upstream NOW, even if it takes longer.
   The PRT is the source of truth — downstream artifacts must match it.
```

## Output: Rework Summary

After completing a rework cycle, document the summary:

```markdown
## Rework Summary: [rework-id]

**Trigger:** [What happened]
**Origin Phase:** [Phase number]
**Scope:** [cosmetic/targeted/moderate/significant/major]

### Changes Made

**Phase [N] — [artifact name]:**
- [Specific change 1]
- [Specific change 2]

**Phase [N+1] — [artifact name]:**
- [Cascaded change 1]

**Phase [N+2] — [artifact name]:**
- [Cascaded change 1]

### Artifacts Modified
- `.prt/{feature}/prt.md` — [what changed: which sections]
- `.prt/{feature}/ux-ideation.md` — [what changed: which screens/journeys]
- `.prt/{feature}/epic-breakdown.md` — [what changed: which epics]

### Verification
- [ ] All affected artifacts are consistent
- [ ] Traceability matrix is up to date (if epic breakdown exists)
- [ ] No orphaned references
- [ ] State.json updated with rework entry
- [ ] Priority distribution still valid

### Lessons Learned
[Optional: What could we have caught earlier? Should an intake question be added?]
```

## Quality Checklist for Rework

Before marking rework as complete:

### Process
- [ ] Rework trigger correctly classified
- [ ] Origin phase correctly identified (not just symptom phase)
- [ ] Scope assessed and confirmed with user (for significant/major)
- [ ] Rework tracked in state.json with unique ID

### Artifacts
- [ ] Origin artifact updated with revision history
- [ ] All downstream artifacts cascaded
- [ ] No orphaned references to removed/changed content
- [ ] Consistency check passed across all phases
- [ ] PRT priority distribution still valid (≤ 60% Must)

### Traceability (if epic breakdown exists)
- [ ] Every PRT story still maps to exactly one epic
- [ ] Every PRT requirement still maps to exactly one epic
- [ ] No orphaned or duplicated entries in traceability matrix
- [ ] Epic dependencies still valid (no new circular dependencies)

### Communication
- [ ] User informed of all changes made
- [ ] If ADLC5 handoff was already done, user notified that PRT has changed
- [ ] Rework summary documented (for significant/major rework)

## Definition of Done

Rework is complete when:
- [ ] Origin phase artifact is updated with revision history
- [ ] All downstream artifacts are cascaded and consistent
- [ ] Consistency check passes across all affected phases
- [ ] State.json reflects completed rework with unique ID
- [ ] User confirms: "Rework looks good, let's continue"
