---
name: discovery-brief-template
description: Template for the discovery-brief.md handoff artifact produced in Phase 3. Structured to be directly consumed by PRT Phase 0 Path C (Discovery Import).
---

# Discovery Brief: {topic-name}

**Created:** {ISO8601 date}
**Topic:** {topic_name}
**Discover Session Status:** Completed

---

## 1. Problem Statement

{3-5 sentence refined problem statement. Not a copy-paste of raw framing — a distilled, stakeholder-ready description of the problem. Answers: what is broken, why it matters, who it affects, and what the consequence of inaction is.}

---

## 2. Who Is Affected

**Primary users:** {who experiences this problem day-to-day — roles, teams, or personas}

**Secondary stakeholders:** {who cares about the outcome but isn't directly in the workflow}

**Scale:** {rough order of magnitude — e.g., 'team of 12 analysts', 'thousands of external advertisers', 'all internal campaign managers'}

---

## 3. The Opportunity

{What becomes possible if this problem is well-solved. Framed positively — what will people be able to do, stop doing, or achieve. Include any quantitative signal if available (e.g., 'could reduce processing time from 45 min to under 5 min').}

---

## 4. Chosen Direction

**Direction:** {direction.chosen — name or short description}

**What it is:**
{2-4 sentence description of the chosen approach. What is it? How does it work at a high level? What is the core mechanism?}

**Why this direction:**
{direction.rationale — why this was chosen given the constraints, goals, and available alternatives. Written so a reader who wasn't in the session understands the reasoning.}

---

## 5. What Was Considered and Not Chosen

The LLM Council surfaced the following directions during exploration. These were considered but not selected for the reasons noted.

| Direction | Why Not Selected |
|-----------|-----------------|
| {direction name from synthesis} | {brief rationale — e.g., 'too complex for team size', 'requires infrastructure we don't have', 'addresses a secondary problem'} |
| {direction name} | {rationale} |

*Note: "Not chosen" does not mean "wrong" — these may be valid future phases or worth revisiting if constraints change.*

---

## 6. Key Trade-offs Resolved

The following architectural or product decisions were made during direction setting:

{For each resolved contradiction from state.json:}

### [Trade-off Name]

**Options considered:**
- Option A ({member(s) that proposed it}): {brief description}
- Option B ({member(s) that proposed it}): {brief description}

**Decision:** {what was chosen}

**Rationale:** {why — one or two sentences}

---

## 7. Scope Sketch

**MVP — what the first release must include:**
{scope_sketch.in_scope — formatted as bullet points}

**Explicitly excluded from this phase:**
{scope_sketch.out_of_scope — formatted as bullet points}

*Note: Exclusions are not permanent — they are scope boundaries for this phase.*

---

## 8. Success Criteria

How we will know this was solved:

{direction.success_criteria — formatted as bullet points}

---

## 9. Constraints

{Combined list of framing.constraints and direction.constraints — formatted as bullet points. Covers technical, organizational, timeline, and scope constraints.}

---

## 10. Risks Acknowledged

{If risk challenge was performed:}
Top risks identified by the Council during Phase 2b. See `.discover/{topic-name}/risk-challenge.md` for the full risk inventory.

| Risk | Category | Likelihood | Impact | Mitigation Signal |
|------|----------|-----------|--------|------------------|
| {risk name} | {category} | {Low/Med/High} | {Low/Med/High} | {mitigation signal} |
| {risk name} | {category} | {Low/Med/High} | {Low/Med/High} | {mitigation signal} |

{If risk challenge was skipped:}
*Risk challenge not performed during this Discover session. Consider running `@discover` risk challenge or adding a risk section during PRT Phase 1.*

---

## 11. Council Insights Summary

**Council used:** {Yes — Claude, GPT, Gemini | No — Solo exploration}

{If council was used:}

**Consensus themes** (appeared in 2+ LLMs independently):
{bullet list of consensus directions/themes from synthesis}

**Notable unique insight** (surfaced by a single LLM — worth keeping in mind):
{1-2 unique insights from exploration-synthesis.md that didn't make it into the chosen direction but are valuable to remember}

{If council was not used:}
*The LLM Council was not enabled for this session. A single-LLM exploration was performed.*

---

## 12. Prior Art and Context

{framing.prior_art — links, references, related work, prior attempts, and what was ruled out. Format as bullet points or short paragraphs.}

*None mentioned.* (if no prior art was captured)

---

## 13. Open Questions

Questions that remain unresolved at the end of the Discover phase. These should be addressed during PRT requirements generation.

| Question | Why It Matters | Owner (if known) |
|----------|---------------|-----------------|
| {question} | {consequence of leaving it unanswered} | {owner or 'TBD'} |
| {question} | {consequence} | {owner or 'TBD'} |

---

*Generated by the Discover skill. See `.discover/{topic-name}/` for all session artifacts including raw council responses.*
