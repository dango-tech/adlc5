---
name: epic-breakdown
description: Phase 3 - Epic Breakdown. Decomposes the approved PRT into independently deliverable, Jira-ready epics. Each epic is a vertical slice through the feature that delivers standalone user value with minimal cross-epic dependencies.
---

# Phase 3: Epic Breakdown

## Purpose

Transform the approved PRT into a set of **independently deliverable epics** that can be uploaded to Jira (or any project tracker). Each epic is a vertical slice of the feature — it cuts across layers (UI, API, data) to deliver a complete user capability, not a horizontal slab of one layer.

The decomposition optimizes for two goals in tension:
1. **Minimal dependencies between epics** — each epic can be planned, staffed, and shipped without waiting on other epics (where possible)
2. **Standalone value on completion** — when an epic ships, a user can do something they couldn't do before

## Output

An epic breakdown document saved to `.prt/{feature-name}/epic-breakdown.md` containing:
- Epic summary table with dependency overview
- Dependency map (text diagram showing the ordering and parallelization opportunities)
- Detailed epic cards with user stories, functional requirements, and per-epic Definition of Done
- Jira import reference (priority mapping, labels, component suggestions)
- Traceability matrix linking every PRT story and requirement to exactly one epic

## Core Principles

### Vertical Slicing, Not Horizontal Layering

**Wrong (horizontal):**
- Epic 1: "Build all API endpoints" — no user value alone
- Epic 2: "Build all UI screens" — blocked by Epic 1
- Epic 3: "Add tests and polish" — blocked by Epic 2

**Right (vertical):**
- Epic 1: "View & Approve Single Invoice" — user can see invoices and act on them end-to-end
- Epic 2: "Search & Filter Invoices" — user can find specific invoices; independent of Epic 3
- Epic 3: "Bulk Actions & Export" — power-user workflows; independent of Epic 2

Each vertical slice includes whatever backend, frontend, and data work is needed to make that capability work.

### The Independence Test

For each epic, ask:
1. **Can a team start this epic without another epic being done?** If yes, no dependency. If no, declare the dependency explicitly and make it as narrow as possible (e.g., "requires Epic 1's list API endpoint" — not "requires all of Epic 1").
2. **Does completing this epic let a user do something new?** If yes, it delivers value. If no, merge it into the nearest epic that does.

### The Foundation Epic Pattern

The first epic (E1) is almost always the **foundation** — the core happy path that establishes the primary data model, base API, and core screen. Subsequent epics depend on E1's foundation but should be independent of each other so they can be parallelized.

```
        E1 (Foundation / MVP)
       / | \
      /  |  \
    E2  E3  E4   ← all depend on E1, but independent of each other
```

This is the ideal shape. If dependencies form a chain (E1 → E2 → E3 → E4), look for ways to flatten — chains serialize the team's work.

## Phase 3 Process

### Step 0: Check Preference

Read `context.generate_epics` from state.json. If `false`, this phase was skipped — the agent should not be here.

### Step 1: Load PRT Content

Read `.prt/{feature-name}/prt.md`. Extract:

**From a Full PRT:**
- All user stories from Section 4 (with priorities)
- All functional requirements from Section 5 (with priorities and acceptance criteria)
- Scope boundaries from Section 3 (in-scope / out-of-scope)
- Dependencies from Section 10
- Non-functional requirements from Section 7 (to identify shared infrastructure needs)

**From a Lite PRT:**
- All user stories from Section 3 (with priorities)
- All requirements from Section 4 (with priorities and acceptance criteria)
- Scope from Section 2

If the UX Ideation artifact exists (`.prt/{feature-name}/ux-ideation.md`), also load:
- Screen/view inventory (Step 3 of Phase 2) — screens often map to epic boundaries
- User journeys (Step 4 of Phase 2) — journeys that share no screens can be separated

### Step 2: Identify Natural Boundaries

Analyze the PRT content to find natural epic boundaries. Use these heuristics in order:

#### Heuristic 1: Priority Tiers as Starting Point

Group stories by MoSCoW priority:
- **Must stories** → These form the MVP epic (E1) or are split across the first 1-2 epics if there are many
- **Should stories** → Each distinct capability becomes a candidate epic
- **Could stories** → Group into 1-2 epics; these are the "nice to have" batch
- **Won't stories** → Excluded from epic breakdown entirely (they're explicitly out of scope)

#### Heuristic 2: User Journey Cohesion

Stories that belong to the same user journey should stay in the same epic. Splitting a journey across epics creates a dependency by definition (the user can't complete the journey until both epics ship).

Ask: "Can a user complete a meaningful task with just the stories in this epic?" If no, the epic is missing stories or is a horizontal slice.

#### Heuristic 3: Data/Screen Affinity

Stories that operate on the same data entity or screen tend to have shared infrastructure (API endpoints, data models, UI components). Keeping them together reduces cross-epic coupling.

However, if a single screen has stories at different priority levels (e.g., "view list" is Must but "filter list" is Should), the Must stories form the foundation epic and the Should stories form an enhancement epic that extends the same screen.

#### Heuristic 4: Persona Boundaries

If the PRT has stories for multiple user roles, and those roles interact with different screens or data, persona boundaries can define epic boundaries. Example:
- Epic 1: "Analyst Workflow" (all stories for the analyst role)
- Epic 2: "Manager Oversight" (all stories for the manager role)

Only use this if the personas don't share screens/journeys. If they do, prefer journey cohesion over persona boundaries.

### Step 3: Draft Epic Structure

For each candidate epic, create:

1. **Epic title** — A short, action-oriented name describing the user capability (not a technical layer). Good: "View & Approve Invoices". Bad: "Backend API Layer".
2. **Priority tier** — Must / Should / Could, inherited from the dominant priority of the stories within
3. **User stories** — The specific stories from the PRT assigned to this epic, with their acceptance criteria
4. **Functional requirements** — The PRT requirements that map to these stories
5. **Dependencies** — Which other epics must be completed first, and specifically what capability is needed (not just "depends on E1" but "depends on E1's invoice list API endpoint")
6. **Value statement** — 1-2 sentences: what a user can do when this epic ships that they couldn't do before
7. **Definition of Done** — 2-4 concrete acceptance conditions specific to this epic

### Step 4: Validate the Decomposition

Run the following checks before presenting to the user:

#### Coverage Check
Every user story and functional requirement from the PRT must appear in exactly one epic. Build the traceability matrix and verify:
- No orphaned stories (story in PRT but not in any epic)
- No duplicated stories (story appears in multiple epics)
- No orphaned requirements (requirement in PRT but not in any epic)

#### Independence Check
Draw the dependency graph. Verify:
- **No circular dependencies** — if E2 depends on E1 and E1 depends on E2, merge them
- **Max chain depth ≤ 3** — if E1 → E2 → E3 → E4, the chain is too long; flatten by finding ways to make E3 or E4 depend on E1 directly instead
- **Parallelization opportunities exist** — after E1, at least 2 epics should be startable concurrently

#### Value Check
For each epic, verify:
- The value statement describes a user-visible capability, not a technical milestone
- A stakeholder reading the value statement would understand why this matters

#### Size Check
- If an epic has more than 8-10 stories, consider splitting it further
- If an epic has only 1 story, consider merging it into the nearest related epic
- Target 3-7 stories per epic as the sweet spot

### Step 5: Present to User for Review

Present the epic breakdown as a summary table + dependency map, then ask the user to review:

```
"Here's how I've broken down the PRT into epics:

[Epic Summary Table]

[Dependency Map]

Key decisions:
- [Why certain stories were grouped together]
- [Why certain stories were separated]
- [Any trade-offs made between independence and cohesion]

Would you like me to adjust the grouping? You can:
1. Move stories between epics
2. Merge two epics into one
3. Split a large epic further
4. Approve this breakdown as-is"
```

### Step 6: Finalize and Save

After user approval:

1. Generate the full epic breakdown document using `templates/epic-breakdown-template.md`
2. Save to `.prt/{feature-name}/epic-breakdown.md`
3. Update state.json: `current_phase: "completed"`, `epic_breakdown: "completed"`
4. Present the file path and proceed to ADLC5 handoff offer

---

## Jira Field Mapping

When generating the epic breakdown, include a reference section that maps PRT fields to Jira fields:

| PRT Field | Jira Field | Notes |
|-----------|-----------|-------|
| Epic title | Epic Name | |
| Value statement | Epic Description | |
| User story (text) | Story Summary | "As a [role], I want..." becomes the summary |
| User story (acceptance criteria) | Story Acceptance Criteria / Description | |
| Must | Priority: Highest | |
| Should | Priority: High | |
| Could | Priority: Medium | |
| Won't | Exclude from import | Already out of scope |
| FR-XXX ID | Story label or custom field | For traceability back to PRT |
| Epic dependency | "is blocked by" link | Create E1 first, then link dependents |

This mapping is advisory — teams should adapt it to their Jira project's custom fields and workflow.

---

## Handling Edge Cases

### Small PRTs (≤ 4 stories)

If the PRT has very few stories, the epic breakdown may produce only 1-2 epics. This is fine. Note to the user:

```
"This PRT has [N] stories, which naturally maps to [1-2] epics. For small features,
a single epic is often the right answer — it avoids artificial splitting."
```

### All-Must PRTs

If every story is Must priority, you can't use priority tiers to separate epics. Fall back to:
1. Journey cohesion — group by user journey
2. Screen affinity — group by screen
3. Ask the user which stories form the absolute minimum viable delivery vs. which Musts could ship in a fast-follow

### Backend-Only Features (no UI)

For features with `ui_facing: false`, epic boundaries come from:
- API endpoint groups (CRUD for entity A vs. CRUD for entity B)
- Integration points (internal service vs. external API)
- Data pipeline stages (ingest → transform → expose)

The same vertical slicing principle applies: each epic should deliver a testable, deployable capability — not just "write the models" or "add the tests."

---

## Quality Checklist for Phase 3

Before marking Phase 3 complete, verify:

### Coverage
- [ ] Every user story from the PRT appears in exactly one epic
- [ ] Every functional requirement from the PRT appears in exactly one epic
- [ ] Traceability matrix is complete with no orphans or duplicates

### Independence
- [ ] No circular dependencies between epics
- [ ] Dependency chain depth ≤ 3
- [ ] At least 2 epics can be parallelized after the foundation epic
- [ ] Dependencies are specific (state what capability is needed, not just "depends on E1")

### Value
- [ ] Each epic has a value statement describing user-visible capability
- [ ] Each epic has a per-epic Definition of Done
- [ ] No epic delivers only a technical layer without user value

### Size
- [ ] No epic has more than 10 stories (split if so)
- [ ] No epic has only 1 story unless it's genuinely atomic (merge if not)
- [ ] Epic count is reasonable for the feature scope (typically 2-5 epics)

### Jira Readiness
- [ ] Priority mapping table included
- [ ] Suggested labels and components provided
- [ ] Import order noted (create foundation epic first)

---

## Definition of Done

Phase 3 is complete when:
- [ ] All PRT stories and requirements are assigned to exactly one epic (traceability verified)
- [ ] Dependency map shows no cycles and max chain depth ≤ 3
- [ ] Each epic delivers standalone user value (value statement passes the "so what?" test)
- [ ] Epic breakdown saved to `.prt/{feature-name}/epic-breakdown.md`
- [ ] state.json updated with `epic_breakdown: "completed"`
- [ ] User approves: "Yes, this breakdown is ready for Jira / ADLC5 handoff"
