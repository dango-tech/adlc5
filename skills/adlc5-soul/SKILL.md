---
name: adlc5-soul
description: ADLC5 supporting reasoning discipline — SOUL, the evidence-driven five-guard reasoning discipline for graph-routed work. Cross-cutting, not a stage. Invoke @adlc5-soul at a gate transition or whenever reasoning feels tangential.
version: 5.0.0
---

# ADLC5 Soul — Reasoning Guard

**Invoke:** `@adlc5-soul for [feature]` — at any gate transition, or the moment work stops tracing to the written problem.

Supports Intelligence, ADLC5’s fifth pillar. The four stages and work graph say *what* happens in what order; SOUL says *how the agent reasons* while doing it. In 4.0, that means preserving consumer-owned acceptance, choosing the minimum sufficient profile, respecting dependency and file-ownership edges, demanding independent verification, and optimizing cost only after the quality floor holds. Rule text (always-on version): [shared/rules/portable/adlc5-soul.md](../../shared/rules/portable/adlc5-soul.md).

## Procedure

1. Read the written problem statement and consumer-owned acceptance — `spec-handoff.md`, acceptance manifest, or the Specify summary in `memory/INDEX.md`. If no written problem exists, that **is** the finding (write-first violation): stop and route to `@adlc5-specify`. Never weaken acceptance to make the implementation pass.
2. Read current stage, selected profile, story dependencies, and evidence state:
   ```bash
   ./scripts/adlc5 state get --feature "{feature}"
   ```
3. Emit a soul check — five lines, one per guard, one sentence each:

   ```text
   SOUL CHECK — {stage} → {next}
   write-first:     does the work trace to the written problem without changing consumer-owned acceptance?
   knowledge-first: did codebase/KB evidence and the current graph inform the approach before invention?
   decide-late:     is this the minimum sufficient profile, with unforced decisions deferred?
   own-the-how:     are spec gaps, dependency and file-ownership edges, and trust boundaries explicit?
   assume-failure:  are unhappy paths tested by independent verification before cost crosses the quality floor?
   verdict:         proceed | refocus | defer
   ```

4. Act on the verdict:
   - **proceed** — continue to the gate (`./scripts/adlc5 gate`). SOUL never replaces gates; it runs before them.
   - **refocus** — name the tangent, drop it or park it in the SDD as a follow-up, re-run the check.
   - **defer** — strike the premature decision, record it as *deferred* in the stage SDD artifact, continue.
5. Append the check to `memory/summaries/{stage}.md` so the next persona inherits it.

## Guard ↔ stage anchors

| Stage | Primary guards |
|-------|----------------|
| Specify | write-first · preserve acceptance ownership |
| Plan | knowledge-first · decide-late · select profile from risk |
| Tasks | decide-late · validate dependency/file ownership |
| Implement | own-the-how · assume-failure · preserve anchors |
| QA / Verify | assume-failure · independent evidence · quality before cost |

All five apply everywhere; the anchors are where each bites hardest.

## Boundaries

- SOUL is advisory reasoning, not a state engine — it writes no `state.json`, adds no gate. `check-gates.py` stays the sole enforcement.
- SOUL never edits acceptance anchors, self-approves waivers, or converts a failed quality run into a cheap success.
- A soul check is ≤ 7 lines. If it grows past that, it has itself gone tangential.
- HITL: surface `refocus`/`defer` verdicts to the user via AskQuestion. Autonomous: record and continue per verdict.

## Model recommendation

**Tier:** reasoning — this is judgment work, not routine execution:

```bash
./scripts/adlc5 resolve-model --tier reasoning [--platform <host>]
```

---

_Provenance: write-first and assume-failure echo Kidlin's and Murphy's laws; decide-late is lean's "decide as late as possible." The guards are named for the behavior, not the attribution._
