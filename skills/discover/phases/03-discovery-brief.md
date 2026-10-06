---
name: discovery-brief
description: Phase 3 - Discovery Brief. Produces the discovery-brief.md handoff artifact from all prior phases. Structured to be directly consumed by PRT Phase 0 Path C (Discovery Import), enabling PRT to skip redundant questions.
---

# Phase 3: Discovery Brief

## Purpose

Produce the discovery brief — a single, structured document that captures everything learned in the Discover skill and hands it off to `@prt` in a format PRT can consume directly. The discovery brief replaces PRT's Phase 0 interview for users who have completed the Discover flow.

A good discovery brief answers the questions PRT would ask in Phase 0, so PRT can skip straight to requirements generation.

## When This Phase Begins

Phase 3 begins after:
- Phase 2 (Direction Setting) is `completed` and direction data is in state.json
- Phase 2b (Risk Challenge) is either `completed` or `skipped`

---

## Step 1: Load All Prior Artifacts

Before generating the discovery brief, read:
- `{workspace}/.discover/{topic-name}/state.json` — framing data, direction data
- `{workspace}/.discover/{topic-name}/framing.md` — full problem framing
- `{workspace}/.discover/{topic-name}/exploration-synthesis.md` — council synthesis
- `{workspace}/.discover/{topic-name}/risk-challenge.md` — risk findings (if exists)

This ensures the brief is comprehensive and nothing from earlier phases is lost.

---

## Step 2: Generate the Discovery Brief

Produce `{workspace}/.discover/{topic-name}/discovery-brief.md` following the template at `templates/discovery-brief-template.md`.

The brief must be self-contained — a reader who has not been part of the Discover session should be able to understand the problem, the chosen direction, the key decisions made, and the risks acknowledged by reading only this document.

**Section guidance:**

**1. Problem Statement**
Synthesize `framing.raw_description` and `framing.pain_points` into a clear, concise 3-5 sentence problem statement. This is not a copy-paste of the framing — it is a refined statement that a stakeholder can act on.

**2. Who Is Affected**
From `framing.who_is_affected`. List primary users, secondary stakeholders, and rough scale.

**3. Opportunity**
From `framing.opportunity`. What becomes possible if this is solved well.

**4. Chosen Direction**
From `direction.chosen` and `direction.rationale`. Describe the selected approach clearly — what it is, why it was chosen over alternatives.

**5. What Was Considered and Rejected**
From the exploration synthesis — document other directions that were surfaced but not chosen, with brief rationale for why they were set aside. This is valuable for future readers and prevents "but what about X?" questions in requirements review.

**6. Key Trade-offs Resolved**
From `direction.resolved_contradictions`. Document each architectural or product decision that was made, the options considered, and the rationale for the choice.

**7. Scope Sketch**
From `direction.scope_sketch`. MVP definition and explicit exclusions.

**8. Success Criteria**
From `direction.success_criteria`. How success will be measured or observed.

**9. Constraints**
Combine `framing.constraints` and `direction.constraints`. All constraints in one place.

**10. Risks Acknowledged**
Summarize top risks from `risk-challenge.md` (if exists), or note "Risk challenge not performed." Include the mitigation signals. This section lets PRT reference risks that were already identified during discovery.

**11. Council Insights Summary**
Brief note on the council process: how many LLMs participated, key consensus themes, and any unique insights that didn't make it into the chosen direction but are worth keeping in mind.

**12. Prior Art and Context**
From `framing.prior_art`. Links, references, related work.

**13. Open Questions**
What is still unknown or unresolved at the end of the Discover phase? These are the questions PRT should address in requirements generation.

---

## Step 3: Review with User

Present a summary of the discovery brief:

```
"The discovery brief is ready. Here's a summary:

**Topic:** {topic_name}
**Chosen Direction:** {direction.chosen}

**Problem:** {2-sentence summary of problem statement}

**MVP Scope:** {scope_sketch — 1-2 sentences}

**Key decisions made:**
{resolved contradictions — as a 2-3 item bullet list}

**Top risks:** {top 2-3 risk names from risk challenge, or 'Risk challenge not performed'}

**Open questions for PRT:** {count} open questions documented

Full brief at .discover/{topic-name}/discovery-brief.md

Does this capture the outcome of our discovery session? Ready to finalize?

1. Looks good — finalize and offer PRT handoff
2. I need to adjust something — (tell me what to change)"
```

---

## Step 4: Finalize and Offer PRT Handoff

Once user approves:

1. Update state:
   ```json
   {
     "phase_status": { "discovery_brief": "completed" },
     "current_phase": "completed"
   }
   ```

2. Offer PRT handoff (from SKILL.md ADLC5 delivery Handoff section):
   ```
   "Would you like to hand this off to PRT for structured requirements?
   I'll copy the discovery brief to .prt/{topic-name}/discovery-brief.md
   so PRT Phase 0 can use it as context and skip questions already answered here.

   1. Yes - Set up PRT handoff
   2. No - I'll handle the PRT handoff manually"
   ```

3. If accepted:
   - Create `.prt/{topic-name}/discovery-brief.md` as a copy of the discovery brief
   - Update `prt_handoff` in state.json
   - Announce: "Discovery brief copied to .prt/{topic-name}/discovery-brief.md. When you're ready, invoke @prt for {topic-name} and it will load the discovery brief as context, skipping questions already answered here."

4. Offer export options:
   ```
   "Your discovery brief is saved at .discover/{topic-name}/discovery-brief.md.

   1. Keep as-is — I'll use it directly in this workspace (default)
   2. Export to project root — Copy discovery-brief.md to {workspace}/{topic-name}-discovery-brief.md for easy sharing"
   ```

---

## What PRT Receives

When PRT's Phase 0 Path C detects `discovery-brief.md`, it maps sections to PRT intake fields:

| Discovery Brief Section | PRT Intake Field |
|------------------------|-----------------|
| Problem Statement | `intake.problem_statement` |
| Who Is Affected | `intake.users` |
| Chosen Direction | Informs problem framing and scope |
| Scope Sketch (MVP) | `intake.in_scope` |
| Scope Sketch (exclusions) | `intake.out_of_scope` |
| Success Criteria | `intake.business_goals` |
| Constraints | `intake.additional_context` |
| Risks Acknowledged | Referenced in PRT Section 10 (Risks/Dependencies) |
| Open Questions | Flagged as `[ASSUMPTION]` items in PRT |

---

## Definition of Done

Phase 3 is complete when:
- [ ] All prior artifacts loaded (framing.md, exploration-synthesis.md, risk-challenge.md if applicable)
- [ ] `discovery-brief.md` generated with all 13 sections complete
- [ ] No sections left as TBD without explanation
- [ ] Summary presented to user and approved
- [ ] PRT handoff offered
- [ ] `phase_status.discovery_brief` set to `"completed"`
- [ ] `current_phase` set to `"completed"`
