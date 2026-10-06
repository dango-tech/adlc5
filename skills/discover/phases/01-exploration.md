---
name: exploration
description: Phase 1 - Exploration. Dispatches the LLM Council (3 subagents, different LLMs) in parallel with the same problem framing. Each independently proposes solution directions. Raw responses are saved to the workspace before synthesis begins.
---

# Phase 1: Exploration (LLM Council)

## Purpose

Explore the solution space by dispatching three independent AI agents — each running a different LLM — with the same problem framing. Because Claude, GPT, and Gemini have different training data, architectures, and reasoning patterns, they surface genuinely different solution directions. This is real cognitive diversity, not simulated variation.

The orchestrator collects all three responses and saves them verbatim. Synthesis happens in Phase 1b.

## When This Phase Begins

Phase 1 begins after:
- Phase 0 (Problem Framing) is `completed` and `framing.md` exists in the workspace
- User preferences are set (`context.council_enabled`, `context.save_qa_log`)

If `context.council_enabled` is `false`, skip the council and perform solo exploration (see [Solo Exploration Fallback](#solo-exploration-fallback)).

---

## Step 1: Announce Council Dispatch

Before spawning subagents, announce what's happening:

```
"I'm dispatching the LLM Council now. Three independent agents — Claude, GPT, and Gemini —
will each explore your problem framing and propose solution directions.

They all receive the same input and work independently. I'll synthesize their responses
once all three report back."
```

Update state:
```json
{
  "current_phase": "1",
  "phase_status": { "exploration": "in_progress" },
  "council": {
    "exploration_responses": {
      "claude": "pending",
      "gpt": "pending",
      "gemini": "pending"
    }
  }
}
```

---

## Step 2: Construct the Council Brief

Read `{workspace}/.discover/{topic-name}/framing.md` and construct the council brief. The brief is the identical prompt sent to all three council members.

**Council Brief Structure:**

```
You are participating in a structured solution exploration exercise.

PROBLEM FRAMING:
---
{full contents of framing.md}
---

TASK:
Explore this problem space and propose 2-3 distinct solution directions.
Do NOT try to combine all ideas into one solution — propose genuinely different approaches
that make different trade-offs.

OUTPUT FORMAT:
You MUST respond using exactly the structure defined in the Council Output Template below.
Do not deviate from this format. The orchestrator that reads your response depends on it.

{full contents of templates/exploration-output-template.md}
```

**Critical:** All three council members receive this **exact same brief**. Do not customize, abbreviate, or modify the brief per member.

---

## Step 3: Spawn Council Subagents in Parallel

Spawn all three subagents simultaneously using the Task tool with the custom discovery council agent types.

```
Task 1: discover-council-claude subagent
  - prompt: [council brief]
  - subagent_type: discover-council-claude
  - description: "Council member Claude — solution exploration"

Task 2: discover-council-gpt subagent
  - prompt: [council brief]
  - subagent_type: discover-council-gpt
  - description: "Council member GPT — solution exploration"

Task 3: discover-council-gemini subagent
  - prompt: [council brief]
  - subagent_type: discover-council-gemini
  - description: "Council member Gemini — solution exploration"
```

**CRITICAL rules for spawning:**
- All three are launched **simultaneously** (same message, parallel Task calls)
- Do NOT pass a `model` parameter in the Task call — each subagent's LLM is already configured independently
- Do NOT pass any workspace context beyond the council brief — council members are stateless
- Council members must NOT read or write any workspace files

---

## Step 4: Receive and Save Responses

As each subagent completes, immediately:

1. **Save the raw response** to the workspace:
   - Claude → `.discover/{topic-name}/council-responses/claude-exploration.md`
   - GPT → `.discover/{topic-name}/council-responses/gpt-exploration.md`
   - Gemini → `.discover/{topic-name}/council-responses/gemini-exploration.md`

2. **Update state.json** for that member:
   ```json
   {
     "council": {
       "exploration_responses": {
         "claude": "received"
       }
     }
   }
   ```

3. **If a member fails** (error, timeout, malformed response):
   - Mark as `failed` in state.json
   - Log the error in the raw response file: `# COUNCIL MEMBER FAILED\n\nError: {error message}`
   - Continue waiting for remaining members

---

## Step 5: Validate Minimum Viable Council

After all three have either responded or failed:

**If 3 of 3 received:** Proceed to Phase 1b.

**If 2 of 3 received:** Announce to user:
```
"Two of three council members responded successfully ({names}). {failed_member} did not respond.
I'll proceed with two perspectives — the synthesis will note the missing member.
Ready to continue?"
```
If yes, proceed to Phase 1b with available responses.

**If 1 of 3 or fewer received:** Stop and notify user:
```
"Only one council member responded successfully. This is not enough for a meaningful synthesis.

Options:
1. Retry the council — attempt to re-spawn the failed members
2. Proceed with solo exploration — I'll explore the problem space myself
3. Wait and retry later"
```

Do not proceed to synthesis with fewer than 2 successful responses.

---

## Step 6: Transition to Phase 1b

After saving all available responses and confirming minimum viable council:

1. Update state:
   ```json
   {
     "phase_status": { "exploration": "completed", "synthesis_review": "in_progress" },
     "current_phase": "1b"
   }
   ```
2. Immediately proceed to Phase 1b (Synthesis Review) — no user confirmation required for this transition
3. Read `phases/01b-synthesis-review.md` and follow its methodology

---

## Solo Exploration Fallback

When `context.council_enabled` is `false`, the orchestrator performs exploration itself:

1. Announce: "Exploring the problem space from a single perspective."
2. Read `framing.md` and generate 3 solution directions using the same structured format from `templates/exploration-output-template.md`
3. Save to `.discover/{topic-name}/council-responses/solo-exploration.md`
4. Update state: `council.enabled: false`, `exploration_responses` all set to `"skipped"`
5. Proceed to Phase 1b — the synthesis step will note this was solo exploration and skip the consensus/divergence analysis
6. Present the three directions directly to the user

---

## State Updates Summary

| Event | State Update |
|-------|-------------|
| Phase 1 begins | `current_phase: "1"`, `phase_status.exploration: "in_progress"`, all `exploration_responses: "pending"` |
| Council member responds | `exploration_responses.{member}: "received"` |
| Council member fails | `exploration_responses.{member}: "failed"` |
| Phase 1 complete | `phase_status.exploration: "completed"`, proceed to `"1b"` |

---

## Definition of Done

Phase 1 is complete when:
- [ ] Council brief constructed from `framing.md`
- [ ] All three council subagents spawned simultaneously
- [ ] Raw responses saved to `council-responses/` for each successful member
- [ ] Response status updated in state.json for each member
- [ ] Minimum viable council check passed (≥2 of 3 responses received)
- [ ] `phase_status.exploration` set to `"completed"`
- [ ] Transition to Phase 1b initiated
