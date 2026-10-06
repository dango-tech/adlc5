---
name: synthesis-review
description: Phase 1b - Synthesis Review. The orchestrator reads all council responses and produces an exploration-synthesis.md that identifies consensus themes, unique insights, and contradictions. Presented to the user before direction setting.
---

# Phase 1b: Synthesis Review

## Purpose

The orchestrator reads all available council responses and synthesizes them into a single, structured exploration report. The goal is NOT to blend or average the perspectives — it is to surface where the LLMs agreed (high-confidence ideas), where one saw something the others missed (unique gems), and where they contradicted each other (genuine trade-offs that require a human decision).

## When This Phase Begins

Phase 1b begins automatically after Phase 1 (Exploration) completes, without requiring user confirmation. The orchestrator immediately reads the council responses and runs synthesis.

---

## Step 1: Load Council Responses

Read all available council response files from the workspace:
- `.discover/{topic-name}/council-responses/claude-exploration.md`
- `.discover/{topic-name}/council-responses/gpt-exploration.md`
- `.discover/{topic-name}/council-responses/gemini-exploration.md`

Skip any files marked as `COUNCIL MEMBER FAILED`. Note which members are included in the synthesis.

---

## Step 2: Parse Structured Sections

Each council response follows the structured format from `templates/exploration-output-template.md`. Parse each response into its structured sections:

- **Direction N: [Name]** — 2-3 directions per member
  - Approach Summary
  - Key Trade-offs
  - Risks
  - Estimated Complexity
  - Who Benefits Most
- **Cross-Cutting Observations** — each member's overall notes

If a response is malformed (does not follow the template), note this in the synthesis and work with what is available.

---

## Step 3: Apply the Synthesis Algorithm

### 3a: Identify All Unique Directions

Create a flat list of all solution directions proposed across all council members (e.g., Claude proposed 3, GPT proposed 3, Gemini proposed 3 = up to 9 total).

### 3b: Group by Thematic Similarity

Group directions that are thematically similar — they may use different names but describe the same fundamental approach. Two directions are the same theme if they share:
- The same core mechanism (e.g., both propose a self-service portal)
- The same primary user benefit (e.g., both target eliminating manual data entry)
- The same architectural pattern (e.g., both propose event-driven automation)

A direction that is unique to one member stays as a standalone item.

### 3c: Classify Each Theme

For each theme or standalone direction, classify it:

| Classification | Definition |
|---------------|-----------|
| **Consensus** | Appeared in 2 or more council members' responses (high confidence — multiple LLMs independently saw this as valuable) |
| **Unique Insight** | Appeared in exactly 1 member's response (potentially high value — worth surfacing, but came from one perspective only) |
| **Contradiction** | Council members proposed fundamentally opposed approaches to the same sub-problem (genuine trade-off requiring user input) |

### 3d: Extract Contradictions

A contradiction exists when two or more council members proposed solutions that are mutually exclusive or reflect opposing philosophies. Examples:

- "Build a custom solution" vs "Use an existing third-party integration"
- "Real-time processing" vs "Batch/async processing"
- "Centralized data model" vs "Federated/distributed data model"
- "Human-in-the-loop approval" vs "Fully automated decision"

Contradictions are not problems — they are the most valuable output of the council. They represent genuine architectural or product decisions that should be surfaced to the user before committing to a direction.

---

## Step 4: Produce exploration-synthesis.md

Save the synthesis to `.discover/{topic-name}/exploration-synthesis.md`:

```markdown
# Exploration Synthesis: {topic-name}

**Created:** {ISO8601 date}
**Council members:** {list of members that responded, e.g., Claude, GPT, Gemini}
**Failed members:** {list of failed members, if any, or 'None'}

---

## Consensus Directions (appeared in 2+ council members)

These directions were independently proposed by multiple LLMs, suggesting higher confidence in their relevance.

### [Direction Name]

**Proposed by:** Claude, GPT *(or whichever members proposed it)*

**What it is:**
{synthesized description — combines the best phrasing from each member's description}

**Why multiple LLMs proposed this:**
{brief explanation of the common reasoning pattern}

**Key trade-offs:**
{consolidated trade-offs from all members who proposed this direction}

**Risks:**
{consolidated risks from all members}

**Complexity estimate:** {Low / Medium / High — note if members disagreed on complexity}

---
*(repeat for each consensus direction)*

---

## Unique Insights (from a single council member)

These were proposed by only one LLM. They may reflect a less obvious angle that is still worth considering.

### [Direction Name] *(from {member})*

**What it is:**
{description from the sole member who proposed it}

**Why it's worth considering:**
{brief framing of why this perspective is valuable}

**Key trade-offs:**
{trade-offs as described by the member}

**Risks:**
{risks as described by the member}

---
*(repeat for each unique insight)*

---

## Contradictions (trade-offs requiring your input)

These are areas where council members proposed fundamentally different approaches. There is no objectively correct answer — the right choice depends on your context and priorities.

### [Trade-off Name]

**The tension:**
{clear description of the opposing positions}

**Option A:** {member(s) that proposed this} — {brief description}
- Advantage: {what this option gets you}
- Cost: {what you give up}

**Option B:** {member(s) that proposed this} — {brief description}
- Advantage: {what this option gets you}
- Cost: {what you give up}

**What to consider:** {framing question or context that helps the user decide}

---
*(repeat for each contradiction)*

---

## Cross-Cutting Observations

Themes noted by one or more council members that apply across directions:

- {observation 1 — attribute to member(s) if relevant}
- {observation 2}
- {observation 3}
```

---

## Step 5: Present Synthesis to User

Present the synthesis in the conversation, then ask:

```
"Here's what the council found.

**{N} consensus directions** — ideas that multiple LLMs independently arrived at.
**{N} unique insights** — angles that only one LLM surfaced.
**{N} contradictions** — genuine trade-offs that require your input before we proceed.

The full synthesis is saved at .discover/{topic-name}/exploration-synthesis.md.

Take a moment to review. When you're ready, we'll move to direction setting — where you'll choose
1-2 directions to pursue and we'll resolve any contradictions.

Ready to proceed to direction setting?"
```

---

## Step 6: Handle Solo Exploration Mode

If `context.council_enabled` was `false` and only one source file exists (`solo-exploration.md`):

1. Skip the consensus/unique/contradiction analysis (these require multiple sources)
2. Present the three directions from the solo exploration directly
3. Note in the synthesis file: "Solo exploration — single LLM perspective. No consensus analysis available."
4. Ask the user to select 1-2 directions to pursue

---

## Step 7: Transition to Phase 2

After user confirms they are ready:

1. Update state:
   ```json
   {
     "phase_status": { "synthesis_review": "completed" },
     "current_phase": "2"
   }
   ```
2. Read `phases/02-direction-setting.md` and follow its methodology

---

## Definition of Done

Phase 1b is complete when:
- [ ] All available council responses read and parsed
- [ ] Synthesis algorithm applied: directions grouped, classified as consensus/unique/contradiction
- [ ] `exploration-synthesis.md` saved to workspace
- [ ] Synthesis presented to user with consensus/unique/contradiction counts
- [ ] User confirmed they are ready to proceed to direction setting
- [ ] `phase_status.synthesis_review` set to `"completed"`
