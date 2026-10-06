---
name: discover
description: Discover - Problem Framing + LLM Council Exploration + Discovery Brief - Guides from a raw idea through structured problem framing, multi-LLM solution exploration via a council of independent AI agents, and direction synthesis, with optional handoff to PRT for structured requirements. The first step in the @discover → @prt → @adlc5-plan pipeline.
version: 1.0.0
author: ADLC5 Contributors
---

# Discover — Problem Framing + LLM Council Exploration Skill

## Intent

This skill guides the exploration phase that happens *before* structured requirements. Starting from a rough idea or problem space, it runs a structured framing interview, then dispatches an LLM Council — three independent AI agents each running a different LLM — to explore the solution space from genuinely different perspectives. The orchestrator synthesizes the council's responses into a discovery brief that feeds directly into `@prt`.

**User invokes:** `@discover for [topic/problem]`

**Agent guides through:**
1. **Phase 0: Problem Framing** — Structured interview to define the problem space, who is affected, the opportunity, constraints, and prior art *(single agent, conversational)*
2. **Phase 1: Exploration** — LLM Council dispatched in parallel; each independently proposes solution directions using a structured format *(3 subagents, different LLMs)*
3. **Phase 1b: Synthesis Review** — Orchestrator merges council responses; surfaces consensus themes, unique insights, and contradictions *(orchestrator-driven)*
4. **Phase 2: Direction Setting** — User selects 1-2 directions; agent helps refine scope, success criteria, and constraints *(single agent + user, convergent)*
5. **Phase 2b: Risk Challenge** — Council red-teams the chosen direction, each independently identifying risks and blind spots *(optional; 3 subagents in parallel)*
6. **Phase 3: Discovery Brief** — Agent produces a structured `discovery-brief.md` as the handoff artifact for `@prt`

**Optional handoff:** After Phase 3, the agent offers to initialize `@prt` by placing the discovery brief in `.prt/{feature-name}/` so PRT Phase 0 (Intake) can load it as context via Path C (Discovery Import).

When used under `@adlc5`, **do not start** until lifecycle state has `git.status` of `completed` or `waived` ([git-isolation.md](../../core/guides/git-isolation.md)):

```bash
./scripts/adlc5 state get --feature "{feature}"
```

On Phase 3 complete, contribute to `.adlc5/{feature}/memory/summaries/spec.md` (distilled brief + path to `.discover/`) per [core/guides/working-memory.md](../../core/guides/working-memory.md) — do not paste full council responses into parent orchestrator chat.

### Model recommendation (first invocation)

```
Recommended model tier: reasoning (orchestrator + council phases).
Council subagents: one model per member (claude / gpt / gemini) — see phases/01-exploration.md.
Resolve: ./scripts/adlc5 resolve-model --tier reasoning [--platform <host>]
See skills/adlc5/guides/model-matrix.md and config.yaml model_profiles.
```

## Workspace Setup

### On First Invocation

When `@discover` is invoked, **ALWAYS**:

1. **Extract topic name** from user's request (convert to kebab-case), or ask for one during Phase 0
2. **Check for state file:** Read `{workspace}/.discover/{topic-name}/state.json`
3. **If state file doesn't exist:**
   - Create `.discover/{topic-name}/` directory in workspace
   - Create initial `state.json` with `current_phase: "discover-0-problem-framing"`
   - Start Phase 0 (Problem Framing) — guided interview
   - After framing completes, ask preferences (see [Initial Preferences Setup](#initial-preferences-setup))
   - Then proceed to Phase 1 (or Phase 1 solo if council disabled)
4. **If state file exists:**
   - Read current phase and resume from there
   - Load context (topic name, framing data, council state, etc.)

### Initial Preferences Setup

**After Phase 0 (Problem Framing) completes, before starting Phase 1, collect preferences via AskQuestion** (Cursor Q&A form). See [core/guides/askquestion-convention.md](../../core/guides/askquestion-convention.md). **Do not** use numbered chat lists.

Call **AskQuestion** with up to 2 questions per call:

| Question id | Maps to | Options |
|-------------|---------|---------|
| `qa_log` | `context.save_qa_log` | yes / no |
| `council_enabled` | `context.council_enabled` | yes (Council) / no (solo) |
| `risk_challenge_enabled` | `context.risk_challenge_enabled` | yes / no (only if council enabled) |
| `facilitation_mode` | `context.facilitation_mode` | `ask_only` (default) / `collaborative` |
| `assumption_policy` | `context.assumption_policy` | `refuse` (default) / `tagged` / `allow` |

Example labels: "Yes — save Q&A log (recommended for teams)", "Yes — enable LLM Council (recommended)", etc.

**Defaults when unset:** `facilitation_mode: ask_only`, `assumption_policy: refuse`. Keep `council_enabled` orthogonal (council vs solo exploration).

If `facilitation_mode` is `ask_only`: do **not** offer unsolicited solution suggestions, scope expansions, or “you might also…” ideas — only ask clarifying questions and reflect the user’s words. `collaborative` may propose options after asking.
If `assumption_policy` is `refuse`: do not invent requirements or facts. `tagged` may record gaps only as `[ASSUMPTION]` after user acknowledgment. `allow` is rare and must be explicit.

If `save_qa_log` is `true`, create and maintain `qa-log.md` throughout the process.
If `save_qa_log` is `false`, skip all Q&A logging.

Store all preferences in state:
```json
{
  "context": {
    "save_qa_log": true,
    "council_enabled": true,
    "risk_challenge_enabled": true,
    "facilitation_mode": "ask_only",
    "assumption_policy": "refuse"
  }
}
```

### State File Schema

The agent MUST create and maintain this file at `{workspace}/.discover/{topic-name}/state.json`:

```json
{
  "topic_name": "string (kebab-case)",
  "current_phase": "0",
  "phase_status": {
    "framing": "not_started|in_progress|completed",
    "exploration": "not_started|in_progress|completed",
    "synthesis_review": "not_started|in_progress|completed",
    "direction_setting": "not_started|in_progress|completed",
    "risk_challenge": "not_started|in_progress|completed|skipped",
    "discovery_brief": "not_started|in_progress|completed"
  },
  "framing": {
    "status": "not_started|in_progress|completed",
    "raw_description": null,
    "who_is_affected": [],
    "pain_points": [],
    "opportunity": null,
    "constraints": [],
    "prior_art": null,
    "success_signal": null,
    "completed_at": null
  },
  "council": {
    "enabled": true,
    "members": ["claude", "gpt", "gemini"],
    "exploration_responses": {
      "claude": "pending|received|failed",
      "gpt": "pending|received|failed",
      "gemini": "pending|received|failed"
    },
    "risk_responses": {
      "claude": "pending|received|failed|skipped",
      "gpt": "pending|received|failed|skipped",
      "gemini": "pending|received|failed|skipped"
    }
  },
  "direction": {
    "chosen": null,
    "rationale": null,
    "scope_sketch": null,
    "success_criteria": [],
    "constraints": []
  },
  "artifacts": {
    "framing": ".discover/{topic-name}/framing.md",
    "council_responses": {
      "claude": ".discover/{topic-name}/council-responses/claude-exploration.md",
      "gpt": ".discover/{topic-name}/council-responses/gpt-exploration.md",
      "gemini": ".discover/{topic-name}/council-responses/gemini-exploration.md"
    },
    "council_risk_responses": {
      "claude": ".discover/{topic-name}/council-responses/claude-risk.md",
      "gpt": ".discover/{topic-name}/council-responses/gpt-risk.md",
      "gemini": ".discover/{topic-name}/council-responses/gemini-risk.md"
    },
    "exploration_synthesis": ".discover/{topic-name}/exploration-synthesis.md",
    "risk_challenge": ".discover/{topic-name}/risk-challenge.md",
    "discovery_brief": ".discover/{topic-name}/discovery-brief.md",
    "qa_log": ".discover/{topic-name}/qa-log.md"
  },
  "context": {
    "save_qa_log": true,
    "council_enabled": true,
    "risk_challenge_enabled": true,
    "facilitation_mode": "ask_only",
    "assumption_policy": "refuse"
  },
  "prt_handoff": {
    "offered": false,
    "accepted": false,
    "prt_path": null
  },
  "rework_history": [],
  "last_updated": "ISO8601 timestamp"
}
```

### Workspace Artifact Structure

All generated files go in the **user's workspace** (NOT in the skills directory):

```
{workspace}/
├── .discover/
│   └── {topic-name}/
│       ├── state.json                    # State tracking (agent creates this)
│       ├── qa-log.md                     # OPTIONAL: Q&A log (only if user opts in)
│       ├── framing.md                    # Phase 0 output: Structured problem framing
│       ├── council-responses/
│       │   ├── claude-exploration.md     # Phase 1: Claude's raw council response
│       │   ├── gpt-exploration.md        # Phase 1: GPT's raw council response
│       │   └── gemini-exploration.md     # Phase 1: Gemini's raw council response
│       ├── exploration-synthesis.md      # Phase 1b: Orchestrator synthesis of council
│       ├── risk-challenge.md             # Phase 2b: Council red-team output (optional)
│       └── discovery-brief.md           # Phase 3: Handoff artifact for @prt
└── .prt/
    └── {feature-name}/
        └── discovery-brief.md           # OPTIONAL: Copy placed here if PRT handoff accepted
```

## Phase Flow & State Management

### Phase Detection Logic

**`current_phase` → step ID mapping** (see [phase-registry.md](../../core/guides/phase-registry.md)):

| `current_phase` | Legacy | `phase_status` key | Phase Guide |
|-----------------|--------|-------------------|-------------|
| `discover-0-problem-framing` | `0` | `framing` | `phases/00-framing.md` |
| `discover-1-council-exploration` | `1` | `exploration` | `phases/01-exploration.md` |
| `discover-2-synthesis-review` | `1b` | `synthesis_review` | `phases/01b-synthesis-review.md` |
| `discover-3-direction-setting` | `2` | `direction_setting` | `phases/02-direction-setting.md` |
| `discover-4-risk-challenge` | `2b` | `risk_challenge` | `phases/02b-risk-challenge.md` |
| `discover-5-discovery-brief` | `3` | `discovery_brief` | `phases/03-discovery-brief.md` |
| `completed` | — | — | Feature complete |

Normalize legacy IDs on read; write new IDs only.

```
1. Extract topic name from user's request (convert to kebab-case)
2. Read {workspace}/.discover/{topic-name}/state.json
3. If file doesn't exist:
   → Create .discover/{topic-name}/ directory
   → Create state.json with current_phase: "0"
   → Start Phase 0 (Problem Framing)
   → After framing: ask preferences (Q&A log, council, risk challenge)
   → Then start Phase 1
4. If file exists:
   → Read current_phase field
   → If "completed": Announce topic is done, ask if user wants to revisit or start a new topic
   → Otherwise: Resume from that phase, load context for continuity
```

### Phase Transitions

**CRITICAL: Never auto-advance phases. Always ask user for confirmation.**

After completing work in a phase:
1. Save the artifact to workspace
2. Update state.json with completed status
3. **AskQuestion:** "Phase [N] complete. Ready to move to Phase [N+1]?" — options: Yes / Revise / Pause (see [askquestion-convention.md](../../core/guides/askquestion-convention.md))
4. If yes → Update state.json current_phase, start next phase
5. If no → Keep in current phase for refinements

**Note on Phase 0 → 1:** After framing completes and preferences are collected, the transition to Phase 1 is automatic. If `council_enabled` is `true`, read `phases/01-exploration.md`. If `false`, perform solo exploration in a single pass.

**Note on Phase 1 → 1b:** This transition is automatic (no user confirmation needed). After council responses are received and saved, the orchestrator immediately performs synthesis. The user confirmation point is at the end of Phase 1b, before advancing to Phase 2.

**Note on Phase 2 → 2b:** After Phase 2 (Direction Setting) completes, if `risk_challenge_enabled` is unset and `council_enabled` is `true`, **AskQuestion** to confirm before dispatching the risk challenge council. If user declines or `risk_challenge_enabled` is `false`, Phase 2b is skipped (`risk_challenge` status set to `"skipped"`) and the agent proceeds to Phase 3.

### LLM Council Execution

When executing a council phase (Phase 1 or Phase 2b), the orchestrator:

1. **Reads the phase guide** — `phases/01-exploration.md` or `phases/02b-risk-challenge.md`
2. **Constructs the council brief** — standardized input from current artifacts
3. **Spawns 3 subagents in parallel** using the Task tool:
   - `discover-council-claude` subagent
   - `discover-council-gpt` subagent
   - `discover-council-gemini` subagent
4. **All three receive the identical prompt** — same council brief + structured output format from `templates/exploration-output-template.md`
5. **Saves raw responses** to `council-responses/` directory
6. **Updates council response status** in state.json as responses arrive
7. **Handles failures gracefully** — if a member fails, proceed with 2 of 3 responses; log `failed` in state
8. **Proceeds to synthesis** (Phase 1b) automatically after all responses received

**Minimum viable council:** At least 2 of 3 members must succeed for council synthesis to proceed. If only 1 succeeds, notify the user and offer to retry or proceed solo.

### PRT Handoff

After Phase 3 completes:

1. **AskQuestion** — PRT handoff:
   - prompt: "Hand off to PRT for structured requirements? (copies discovery brief to `.prt/{feature}/`)"
   - options: `yes` (Set up PRT handoff) / `no` (Manual handoff)
2. If accepted: Create `.prt/{feature-name}/discovery-brief.md` as a copy of the discovery brief
3. Update `prt_handoff` in state.json
4. Announce: "Discovery brief copied to .prt/{feature-name}/discovery-brief.md. When you're ready, invoke @prt for {feature-name} and it will load the discovery brief as context."

## Phase Reference Guides

The agent should read these files from the skills directory for detailed methodology:

- **Phase 0 (Problem Framing):** Read `phases/00-framing.md` — Guided problem framing interview, framing data schema, output format
- **Phase 1 (Exploration):** Read `phases/01-exploration.md` — Council dispatch methodology, council brief construction, parallel execution rules, graceful degradation
- **Phase 1b (Synthesis Review):** Read `phases/01b-synthesis-review.md` — Merge algorithm, consensus/divergence/contradiction detection, synthesis output format
- **Phase 2 (Direction Setting):** Read `phases/02-direction-setting.md` — Convergence methodology, direction refinement, scope sketching
- **Phase 2b (Risk Challenge):** Read `phases/02b-risk-challenge.md` — Red team council dispatch, risk synthesis methodology
- **Phase 3 (Discovery Brief):** Read `phases/03-discovery-brief.md` — Discovery brief production, handoff artifact format
- **Agent Instructions:** Read `guides/discover-agent-instructions.md` — Facilitator persona, tone, behavioral rules
- **Exploration Output Template:** Read `templates/exploration-output-template.md` — Structured format council members follow for exploration briefs (risk challenge format is defined inline in `phases/02b-risk-challenge.md`)
- **Discovery Brief Template:** Read `templates/discovery-brief-template.md` — Handoff artifact template

## Resuming Work

If user invokes `@discover` in a workspace with existing state:

1. **Extract topic name** from user's request
2. **Read state file:** `{workspace}/.discover/{topic-name}/state.json`
3. **Announce context:** "Resuming Discover for '{topic_name}'. Currently in Phase {N}: {phase_name}."
4. **Load artifacts:** Read relevant files from workspace
5. **Continue from current phase**

**Note:** If user doesn't specify topic name, list available topics by scanning the `.discover/` directory:
1. List all subdirectories under `{workspace}/.discover/` (each subdirectory is a topic)
2. For each subdirectory, read `state.json` to get `current_phase` and phase status
3. Present the list to the user:

```
User: "@discover"
Agent: "Found existing Discover projects in this workspace:
        1. ai-expense-automation (Phase 1: Exploration - in progress)
        2. vendor-onboarding (Phase 2: Direction Setting)
        3. campaign-analytics (Phase 3: Discovery Brief)

        Which topic would you like to continue with, or would you like to start a new one?"
```

If the `.discover/` directory doesn't exist or is empty, treat this as a new invocation and start Phase 0.

## Agent Instructions Summary

### On Every Invocation

1. **Extract topic name** from user's request (or list available if not specified)
2. **Read workspace state:** `{workspace}/.discover/{topic-name}/state.json`
3. **Determine phase:** Extract current_phase or start at 0
4. **Load agent instructions:** Read `guides/discover-agent-instructions.md` for persona, tone, and behavioral rules
5. **Load phase guide:** Read appropriate `phases/{N}-*.md` file
6. **Load workspace artifacts:** Read relevant framing, council responses, synthesis, direction files
7. **Execute phase:** Follow methodology from phase guide
8. **Save artifacts:** Write to `{workspace}/.discover/{topic-name}/...`
9. **Update Q&A log (if enabled):** If `context.save_qa_log` is `true`, append Q&A to `qa-log.md`
10. **Update state:** Write updated `{workspace}/.discover/{topic-name}/state.json`
11. **Ask for confirmation:** Before advancing to next phase (except 0 → 1, 1 → 1b which are automatic)

### Never Do

- ❌ Auto-advance phases without user confirmation (except 0 → 1 and 1 → 1b)
- ❌ Skip state updates
- ❌ Assume phase without reading state
- ❌ Create artifacts without proper workspace paths
- ❌ Forget to load context when resuming
- ❌ Write to state.json from within council subagents — only the orchestrator updates state
- ❌ Run Phase 1 council without reading `phases/01-exploration.md` first
- ❌ Spawn more than 3 council subagents concurrently
- ❌ Proceed with synthesis if fewer than 2 of 3 council members responded successfully
- ❌ Skip the synthesis step — always merge and present council findings before asking user to choose a direction
- ❌ Let a council member's output influence another council member — each runs independently with the same input
- ❌ Skip the PRT handoff offer after Phase 3 completes
- ❌ Generate a discovery brief from thin framing — Phase 0 must produce complete framing data first
- ❌ Make untracked changes to completed artifacts

### Always Do

- ✅ Extract topic name first
- ✅ Read state from `.discover/{topic-name}/state.json`
- ✅ Run Phase 0 (Problem Framing) for new topics — guided interview
- ✅ Load `guides/discover-agent-instructions.md` for persona and behavioral rules
- ✅ Save all artifacts to workspace
- ✅ Update state after significant actions
- ✅ Log all Q&A exchanges to `qa-log.md` immediately (if enabled)
- ✅ **AskQuestion** before phase transitions (except automatic internal transitions) (except 0 → 1 and 1 → 1b)
- ✅ Load phase guides for detailed methodology
- ✅ Use workspace-relative paths for all artifacts
- ✅ Use framing data from Phase 0 as the council brief input — do not ask redundant questions
- ✅ Save all council raw responses to `council-responses/` before synthesizing
- ✅ Present the synthesis with explicit consensus/unique/contradiction sections
- ✅ Offer PRT handoff after Phase 3 completes
- ✅ Handle council member failures gracefully — log, continue with available responses
- ✅ In Phase 1b: Surface contradictions as trade-offs for the user, not as problems to resolve unilaterally

## Quality Standards

Every phase output must meet these standards:
- **Problem Framing:** Complete — problem statement, affected parties, pain points, opportunity, constraints all populated; no vague or thin framing
- **Council Responses:** All responses in the exact structured format from `templates/exploration-output-template.md`; saved as raw files before synthesis
- **Synthesis:** Explicit consensus/unique/contradiction sections; no opinion blending that obscures differences
- **Direction Setting:** Chosen direction documented with rationale, scope sketch, success criteria, and constraints
- **Risk Challenge:** Each risk attributed to the council member that identified it; risks de-duplicated before presentation
- **Discovery Brief:** All sections complete; ready for direct consumption by PRT Phase 0 Path C (Discovery Import)
- **Tone:** Curious, collaborative, exploratory — like a senior product strategist facilitating a discovery workshop
