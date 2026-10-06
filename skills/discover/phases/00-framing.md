---
name: framing
description: Phase 0 - Problem Framing. Structured interview that gathers all context about the problem space before exploration begins. Produces framing.md as the input to the LLM Council.
---

# Phase 0: Problem Framing

## Purpose

Gather a clear, complete picture of the problem space before any solution thinking begins. This phase is deliberately divergent and open-ended — the goal is to understand the problem deeply, not to sketch solutions.

The output (`framing.md`) becomes the council brief input for Phase 1. A thin or vague framing produces thin council output. Invest time here.

**Facilitation (before preferences are stored, treat as `ask_only`):** do not propose architectures, features, or “typical” solutions. Ask one focused question at a time; mirror the user’s language. After preferences: if `context.facilitation_mode` is `ask_only` (default), keep that discipline for the rest of Discover. If `context.assumption_policy` is `refuse` (default), do not invent missing facts — ask or leave gaps explicit.

## Why This Phase Exists

Jumping straight to solution exploration without structured framing produces:
- Solutions that solve the wrong problem
- Council output that's superficial because the problem context is unclear
- Discovery briefs that PRT cannot easily consume

Phase 0 front-loads all problem understanding so Phase 1 can produce high-quality, specific exploration.

## Entry Point

Phase 0 begins with a welcome message:

```
"Welcome to the Discover skill. I'll help you explore the problem space and identify
the most promising solution directions before we commit to structured requirements.

Let's start by understanding the problem deeply. I'll ask you a series of focused
questions — there are no wrong answers at this stage.

What problem or opportunity are you trying to explore today?"
```

---

## Interview Sequence

Each step asks one focused question, waits for the answer, then moves to the next. Do not batch multiple questions into a single message.

### Step 1: Opening Question (already asked in welcome)

Capture the user's initial framing in their own words. Store this raw description — it's valuable context even if it's rough.

Store as `framing.raw_description`.

### Step 2: Who Is Affected

```
"Who experiences this problem? Tell me about the people at the center of it.

- Who are the primary people affected? (roles, teams, or personas — e.g., 'Finance Ops Analysts', 'Campaign Managers', 'end customers')
- Are there secondary groups who are affected differently?
- Roughly how many people are we talking about?"
```

Store as `framing.who_is_affected`.

### Step 3: Pain Points — What's Broken Today

```
"What does the current experience look like? Help me feel the pain.

- What does someone have to do today that is broken, slow, manual, or frustrating?
- What workarounds exist, and why are they inadequate?
- Is there a specific moment or step where things fall apart?"
```

Store as `framing.pain_points`.

### Step 4: The Opportunity

```
"Now let's flip it: if this problem were solved well, what would be different?

- What would someone be able to do that they can't do today?
- What would they stop having to do?
- What business outcome would improve (time saved, cost reduced, revenue unlocked, risk reduced)?"
```

Store as `framing.opportunity`.

### Step 5: Constraints and Context

```
"What constraints are we working within?

Examples:
- Technical: 'Must integrate with our existing Salesforce setup', 'Backend is Python/Django'
- Organizational: 'Can't change the approval workflow', 'Must go through the security review process'
- Timeline: 'Needs to be in market before Q3', 'This is a hard regulatory deadline'
- Budget/Scope: 'Small team, 2 engineers for 6 weeks'
- Anything we must NOT do in this exploration

Skip anything that doesn't apply."
```

Store as `framing.constraints`.

### Step 6: Prior Art

```
"Has anyone tackled this before? (Optional — skip if nothing comes to mind)

- Has this been attempted internally before? What happened?
- Are there tools, competitors, or analogous solutions in other industries that are relevant?
- Is there existing work (Figma mockups, Jira epics, tech spikes, research docs) I should know about?
- What has already been ruled out, and why?"
```

Store as `framing.prior_art`.

### Step 7: Success Signal

```
"Last question: how would you know this was solved?

If we fast-forward 6 months and this problem is well addressed, what is different?
What would you be able to measure, observe, or feel that would tell you it worked?"
```

Store as `framing.success_signal`.

### Step 8: Review Summary

After collecting all answers, present a summary:

```
"Here's what I've captured about the problem space:

**Topic:** {topic_name}

**Who is affected:** {who_is_affected}

**The pain today:**
{pain_points — formatted as bullet points}

**The opportunity:**
{opportunity}

**Constraints:**
{constraints — formatted as bullet points, or 'None identified'}

**Prior art / context:**
{prior_art or 'None mentioned'}

**Success signal:**
{success_signal}

Does this accurately reflect the problem? This framing will guide the exploration phase.

1. Looks good — proceed to preferences and exploration
2. I need to adjust something — (tell me what to change)"
```

If the user wants changes, update the relevant fields and re-present the summary.

---

## After Framing: Transition

Once the user approves the summary:
1. Save framing data to state.json under the `framing` object
2. Set `framing.status: "completed"` and `framing.completed_at` to current timestamp
3. Save `framing.md` to workspace (see [Framing Output Format](#framing-output-format))
4. Proceed to Initial Preferences Setup (Q&A logging, council, risk challenge) — see the "Initial Preferences Setup" section in `SKILL.md`
5. After preferences are collected, set `current_phase: "1"` in state.json
6. Then proceed to Phase 1

**Note:** Do not set `current_phase` to `"1"` until preferences are fully collected. If the session is interrupted during preferences, the agent should resume at Phase 0 and re-ask preference questions.

---

## Framing Output Format

Save `{workspace}/.discover/{topic-name}/framing.md` with the following structure:

```markdown
# Problem Framing: {topic-name}

**Created:** {ISO8601 date}
**Status:** Completed

## Raw Description

{framing.raw_description — user's original words, unedited}

## Who Is Affected

{who_is_affected — formatted as a clear paragraph or bullet list}

## Pain Points — What's Broken Today

{pain_points — formatted as bullet points; specific and concrete}

## The Opportunity

{opportunity — what becomes possible if this is solved}

## Constraints

{constraints — formatted as bullet points, or 'None identified'}

## Prior Art and Context

{prior_art or 'None mentioned'}

## Success Signal

{success_signal — how we'd know it worked}
```

This file becomes the **council brief** — the exact input given to all three LLM Council members in Phase 1.

---

## Framing Data Schema

The framing object stored in state.json:

```json
{
  "framing": {
    "status": "not_started|in_progress|completed",
    "raw_description": "string",
    "who_is_affected": ["string"],
    "pain_points": ["string"],
    "opportunity": "string",
    "constraints": ["string"],
    "prior_art": "string|null",
    "success_signal": "string",
    "completed_at": "ISO8601 timestamp"
  }
}
```

---

## Skipping or Shortcutting Phase 0

Phase 0 cannot be fully skipped — the council needs a complete framing to produce useful output.

**However**, if the user provides a highly detailed description in their initial `@discover for [topic]` invocation (covers who is affected, pain points, opportunity, and constraints), the agent may:

1. Extract framing fields directly from the description
2. Present a pre-populated summary and ask for confirmation
3. Skip the step-by-step interview and jump straight to the review summary

The agent should announce: "Your description is detailed enough to populate the problem framing. Let me show you what I've extracted — you can adjust before we proceed."

**If the description is thin (just a topic name or one sentence), the agent MUST run the full interview.**

---

## Definition of Done

Phase 0 is complete when:
- [ ] All required fields populated: `who_is_affected`, `pain_points`, `opportunity`, `success_signal`
- [ ] At least one of: `constraints` or `prior_art` addressed (even if user says 'none')
- [ ] Summary presented to user and approved
- [ ] Framing data saved to state.json
- [ ] `framing.md` saved to workspace
- [ ] `framing.status` set to `"completed"`
