---
name: risk-challenge
description: Phase 2b - Risk Challenge (optional). The LLM Council is re-dispatched as a red team. Each member independently identifies risks, blind spots, and unstated assumptions in the chosen direction. The orchestrator synthesizes into a risk-challenge.md.
---

# Phase 2b: Risk Challenge (LLM Council Red Team)

## Purpose

Put the chosen direction under adversarial scrutiny before writing requirements. Each council member independently acts as a critic — identifying risks, blind spots, questionable assumptions, and failure modes in the direction the user has selected.

Because each LLM has different reasoning patterns, they will surface different categories of risk. One might focus on technical risks, another on organizational risks, another on user adoption risks. The orchestrator synthesizes these into a prioritized risk inventory.

## When This Phase Begins

Phase 2b begins when the user confirms they want a risk challenge (set during Phase 2, Step 8). If `context.risk_challenge_enabled` is `false` or user declined, this phase is skipped with `phase_status.risk_challenge: "skipped"`.

---

## Step 1: Announce Risk Challenge

```
"Dispatching the Council for a red-team review of '{chosen direction}'.

Each member will independently challenge this direction — looking for risks, blind spots,
and unstated assumptions. I'll synthesize their findings once all three report back."
```

Update state:
```json
{
  "current_phase": "2b",
  "phase_status": { "risk_challenge": "in_progress" },
  "council": {
    "risk_responses": {
      "claude": "pending",
      "gpt": "pending",
      "gemini": "pending"
    }
  }
}
```

---

## Step 2: Construct the Risk Challenge Brief

Read the direction data from state.json and `framing.md`, and construct the red-team brief:

```
You are participating in a structured risk assessment exercise.

PROBLEM FRAMING:
---
{full contents of framing.md}
---

CHOSEN DIRECTION:
**Direction:** {direction.chosen}
**Rationale:** {direction.rationale}
**Scope (MVP):** {direction.scope_sketch}
**Success criteria:**
{direction.success_criteria — as bullet points}
**Constraints:**
{direction.constraints — as bullet points}

TASK:
Act as a critical reviewer. Your job is to challenge this direction — not to improve it or
propose alternatives, but to identify what could go wrong.

Look for:
- Technical risks (implementation complexity, integration failure points, scalability issues)
- User/adoption risks (will users actually adopt this? are there workflow or behavior change challenges?)
- Organizational risks (stakeholder alignment, process dependencies, change management)
- Assumption risks (what is this direction taking for granted that might not be true?)
- Scope risks (what might expand in ways that are hard to predict from here?)
- Timing/sequencing risks (what must be true first before this can succeed?)

Be specific. Vague risks like "this could be complex" are not useful.
Name the specific thing that could fail and why.

OUTPUT FORMAT:
You MUST respond using exactly the Risk Challenge Output structure below.
Do not deviate. The orchestrator that reads your response depends on this format.

## Risk Challenge Output

### Risks

For each risk, use this structure:

**Risk [N]: [Short Name]**
- **Category:** Technical | User/Adoption | Organizational | Assumption | Scope | Timing
- **Description:** {what specifically could go wrong, and why}
- **Likelihood:** Low | Medium | High
- **Impact if realized:** Low | Medium | High
- **Mitigation signal:** {what would reduce this risk — a decision, a validation step, or a constraint}

List 4-7 risks. More than 7 is noise; fewer than 4 suggests insufficient scrutiny.

### Top Concern

**What is the single biggest risk in this direction?**
{One paragraph. Be direct.}

### Unstated Assumptions

List 2-4 assumptions this direction is taking for granted that have not been validated:

- **Assumption:** {what the direction assumes is true}
  **Why it matters if wrong:** {consequence if the assumption is false}
```

**Critical:** Same brief sent to all three council members verbatim. Do not customize per member.

---

## Step 3: Spawn Risk Challenge Council in Parallel

Spawn all three subagents simultaneously using the Task tool, identical to Phase 1, with custom discovery council agent types.

```
Task 1: discover-council-claude subagent
  - prompt: [risk challenge brief]
  - subagent_type: discover-council-claude
  - description: "Council member Claude — risk challenge"

Task 2: discover-council-gpt subagent
  - prompt: [risk challenge brief]
  - subagent_type: discover-council-gpt
  - description: "Council member GPT — risk challenge"

Task 3: discover-council-gemini subagent
  - prompt: [risk challenge brief]
  - subagent_type: discover-council-gemini
  - description: "Council member Gemini — risk challenge"
```

Follow the same parallel execution rules from Phase 1: do NOT pass a `model` parameter, save raw responses, update state, handle failures gracefully, require ≥2 of 3 responses.

Save raw responses to:
- `.discover/{topic-name}/council-responses/claude-risk.md`
- `.discover/{topic-name}/council-responses/gpt-risk.md`
- `.discover/{topic-name}/council-responses/gemini-risk.md`

---

## Step 4: Synthesize Risk Findings

After receiving responses, synthesize into `risk-challenge.md`:

### De-duplication

Group risks that describe the same failure mode (even if named differently). When multiple members identified the same risk, note that it appeared in 2 or 3 responses — this increases its significance.

### Prioritization

Sort risks by a combination of:
- **Frequency** — mentioned by 2+ council members → elevate
- **Impact** — High impact risks surface first
- **Likelihood** — High likelihood + High impact = critical

### Risk Challenge Output Format

Save to `.discover/{topic-name}/risk-challenge.md`:

```markdown
# Risk Challenge: {topic-name} — {chosen direction}

**Created:** {ISO8601 date}
**Council members:** {members that responded}
**Direction assessed:** {chosen direction}

---

## Critical Risks (High Likelihood × High Impact or flagged by 2+ members)

### [Risk Name]
- **Category:** {category}
- **Identified by:** {member(s)}
- **Description:** {consolidated description}
- **Likelihood:** High | Medium
- **Impact:** High
- **Mitigation signal:** {consolidated mitigation signals from all members}

---

## Significant Risks

*(Medium likelihood or impact, or unique to one member but important)*

### [Risk Name]
*(same structure)*

---

## Watch Items (Lower priority, worth tracking)

*(Low likelihood or impact — still worth documenting)*

---

## Unstated Assumptions

| Assumption | Flagged by | Consequence if Wrong |
|------------|-----------|---------------------|
| {assumption} | {member(s)} | {consequence} |

---

## Top Concerns (as stated by council members)

**Claude's top concern:** {verbatim or close paraphrase}

**GPT's top concern:** {verbatim or close paraphrase}

**Gemini's top concern:** {verbatim or close paraphrase}
```

---

## Step 5: Present Risk Summary to User

Present a concise summary in the conversation:

```
"The Council red-teamed '{chosen direction}'. Here's what they found:

**{N} critical risks** — high likelihood or impact, flagged by multiple members
**{N} significant risks** — worth addressing before requirements
**{N} watch items** — lower priority, monitor
**{N} unstated assumptions** — not yet validated

Top concern (most commonly flagged): {top risk name — one sentence description}

Full details at .discover/{topic-name}/risk-challenge.md

Would you like to discuss any of these before we write the discovery brief,
or are you ready to proceed?"
```

---

## Step 6: Optional Risk Discussion

If the user wants to discuss specific risks:
- Address each one conversationally
- If a risk causes the user to reconsider the direction, offer to return to Phase 2 (Direction Setting)
- Update `direction.constraints` or `direction.scope_sketch` if the risk discussion surfaces new decisions

---

## Step 7: Transition to Phase 3

After user confirms they are ready:

1. Update state:
   ```json
   {
     "phase_status": { "risk_challenge": "completed" },
     "current_phase": "3"
   }
   ```
2. Read `phases/03-discovery-brief.md` and follow its methodology

---

## Definition of Done

Phase 2b is complete when:
- [ ] Risk challenge brief constructed from direction data and framing.md
- [ ] All three council subagents spawned simultaneously
- [ ] Raw risk responses saved to `council-responses/` for each successful member
- [ ] Risk findings de-duplicated and prioritized
- [ ] `risk-challenge.md` saved to workspace
- [ ] Risk summary presented to user
- [ ] User confirmed they are ready to proceed (or direction was revised)
- [ ] `phase_status.risk_challenge` set to `"completed"`
