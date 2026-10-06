---
name: direction-setting
description: Phase 2 - Direction Setting. User selects 1-2 directions from the synthesis. Agent helps resolve contradictions, refine scope, define success criteria, and document constraints. Produces a focused direction document.
---

# Phase 2: Direction Setting

## Purpose

Converge. The user has seen the full exploration synthesis — multiple solution directions, unique insights, and trade-offs. This phase helps them select 1-2 directions to pursue and refines each chosen direction into a clear, documented position that the discovery brief can be built from.

This is the most decision-intensive phase. The agent's role is to facilitate, not to decide. Ask questions that help the user clarify their thinking. Surface implications without pushing toward a predetermined answer.

## When This Phase Begins

Phase 2 begins after the user confirms they are ready to proceed from Phase 1b (Synthesis Review).

---

## Step 1: Direction Selection

Start by asking the user to select from the synthesis:

```
"Looking at the exploration synthesis, which direction(s) feel most promising to pursue?

You can:
- Choose one direction to focus on
- Choose two directions to explore further (if they're complementary, not competing)
- Combine elements from different directions — tell me what you'd take from each
- Propose a direction the council didn't surface — your own synthesis

What resonates?"
```

Wait for the user's response. They may reference directions by name, by number, or describe a blend. Capture their intent precisely.

Store the selection as `direction.chosen` (direction name(s) or description).

---

## Step 2: Resolve Contradictions

If the synthesis identified contradictions, address each one that is relevant to the chosen direction(s):

For each relevant contradiction, present it clearly and ask the user to decide:

```
"One of the trade-offs from the council was:

[Contradiction Name]
- Option A (proposed by {member}): {description}
  → Gets you: {advantage}
  → Costs you: {cost}

- Option B (proposed by {member}): {description}
  → Gets you: {advantage}
  → Costs you: {cost}

Which fits your context better? Or is there a third option you'd prefer?"
```

Address contradictions one at a time. Do not stack multiple trade-offs into a single question.

Store resolutions in state:
```json
{
  "direction": {
    "resolved_contradictions": [
      {
        "name": "string",
        "resolution": "option_a|option_b|custom",
        "rationale": "string"
      }
    ]
  }
}
```

---

## Step 3: Scope Sketch

Help the user sketch the rough scope of the chosen direction:

```
"Let's sketch the rough scope for '{chosen direction}'.

- What does the MVP (minimum viable version) look like?
  What is the smallest thing we could build that delivers real value?
- What is explicitly out of scope for this phase?
  (Even if it's a good idea — naming exclusions now prevents scope creep)
- Is this a new surface (net new UI/feature) or an evolution of something existing?"
```

Store as `direction.scope_sketch`.

---

## Step 4: Success Criteria

```
"How will you know this direction worked?

List 2-4 success criteria — they can be quantitative ('reduce processing time by 50%')
or qualitative ('the ops team stops needing to use the manual workaround').

These don't need to be final — we'll refine them in the PRT. But having a signal now
helps us evaluate whether the direction is worth pursuing."
```

Store as `direction.success_criteria`.

---

## Step 5: Additional Constraints

```
"Any constraints specific to this direction that we didn't cover in the framing?

For example:
- Technical constraints this direction introduces
- Stakeholder or approval considerations
- Timeline dependencies
- Anything this direction must NOT do

(Skip if nothing new comes to mind — we captured constraints in the framing.)"
```

Store as `direction.constraints`.

---

## Step 6: Direction Rationale

Ask the user to articulate *why* this direction over the alternatives:

```
"Last thing: why this direction? What is it about '{chosen direction}' that makes it
the right bet given your constraints and goals?

This doesn't need to be long — one or two sentences is fine. It helps explain the
reasoning to anyone reading the discovery brief later."
```

Store as `direction.rationale`.

---

## Step 7: Direction Summary Review

Present a summary of the chosen direction:

```
"Here's the direction we're pursuing:

**Direction:** {chosen direction name/description}
**Rationale:** {rationale}

**Scope (MVP):** {scope_sketch}
**Explicitly excluded:** {out_of_scope items or 'None identified'}

**Success criteria:**
- {criterion 1}
- {criterion 2}

**Constraints:**
{constraints or 'None beyond those captured in framing'}

Does this accurately capture the direction? I'll use this to produce the discovery brief.

1. Looks good — proceed
2. I need to adjust something — (tell me what to change)"
```

If the user wants changes, update the relevant fields and re-present the summary.

---

## Step 8: Risk Challenge Decision

After direction is confirmed, check `context.risk_challenge_enabled`:

**If `true`:** Ask:
```
"Ready to red-team this direction with the Council?

Each council member will independently identify risks, blind spots, and assumptions
in '{chosen direction}'. This usually surfaces 3-6 issues worth addressing before
we write requirements.

1. Yes — run the risk challenge
2. No — skip to discovery brief"
```

**If `false`:** Skip directly to Phase 3.

---

## Step 9: State Update and Transition

1. Save direction data to state.json:
   ```json
   {
     "direction": {
       "chosen": "string",
       "rationale": "string",
       "scope_sketch": "string",
       "success_criteria": ["string"],
       "constraints": ["string"],
       "resolved_contradictions": [...]
     },
     "phase_status": { "direction_setting": "completed" }
   }
   ```

2. If risk challenge accepted:
   - Set `current_phase: "2b"`
   - Read `phases/02b-risk-challenge.md`

3. If risk challenge skipped:
   - Set `phase_status.risk_challenge: "skipped"`, `current_phase: "3"`
   - Read `phases/03-discovery-brief.md`

---

## Facilitation Notes

**When the user is unsure between two directions:**
Help them compare along the dimensions that matter most given their constraints. Ask: "Given your timeline / team size / risk tolerance, which direction has a better chance of delivering real value in the first release?"

**When the user wants to combine everything:**
Gently challenge this. "Which 2-3 capabilities would you need to have vs nice to have? If you could only build one part of this, what delivers the most value?" Scope creep in the direction-setting phase creates bloated requirements.

**When contradictions don't seem to matter:**
Some contradictions may not be relevant to the chosen direction. Skip those — only resolve contradictions that affect the direction the user is pursuing.

---

## Definition of Done

Phase 2 is complete when:
- [ ] Direction(s) chosen and documented in state.json
- [ ] All relevant contradictions resolved
- [ ] Scope sketch captured (MVP and explicit exclusions)
- [ ] Success criteria captured (≥2 criteria)
- [ ] Direction rationale captured
- [ ] Summary presented to user and approved
- [ ] Risk challenge decision made
- [ ] `phase_status.direction_setting` set to `"completed"`
