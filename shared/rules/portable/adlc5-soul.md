
# ADLC5 Soul — Five-Guard Reasoning Discipline

The reasoning discipline supporting Intelligence, ADLC5’s fifth pillar. Not a lifecycle stage — a reasoning discipline across Specify → Plan → Tasks → Implement. In 4.0 it keeps graph-routed work anchored to consumer-owned acceptance, selects the minimum sufficient profile, respects dependency and file-ownership edges, requires independent verification, and optimizes only after the quality floor holds.

## The five guards, mapped to the lifecycle

| Guard | Discipline | Anchors |
|-------|-----------|---------|
| **write-first** — a problem written down clearly is half solved | Trace work to the written problem and preserve consumer-owned acceptance; never rewrite the target to fit the patch. | Specify + every stage entry |
| **knowledge-first** — understanding precedes code | Consult codebase/KB evidence and the current graph before inventing. | Plan |
| **decide-late** — when a decision isn't necessary, don't decide | Choose the minimum sufficient profile from actual risk; defer choices no gate forces. | Plan · Tasks |
| **own-the-how** — accepted outcomes need explicit execution | Surface gaps and honor dependency and file-ownership edges plus stated trust boundaries. | Tasks · Implement |
| **assume-failure** — anything that can go wrong, will | Test unhappy paths with independent verification; optimize cost only among runs above the quality floor. | Implement · Verify · QA |

## Soul check (at every gate transition, and whenever drift is suspected)

Five lines, one per guard, then a verdict. Keep each line to one sentence.

```text
SOUL CHECK — {stage} → {next}
write-first:     does the work trace to the written problem without changing consumer-owned acceptance?
knowledge-first: did codebase/KB evidence and the current graph inform the approach before invention?
decide-late:     is this the minimum sufficient profile, with unforced decisions deferred?
own-the-how:     are spec gaps, dependency and file-ownership edges, and trust boundaries explicit?
assume-failure:  are unhappy paths tested by independent verification before cost crosses the quality floor?
verdict:         proceed | refocus | defer
```

- **proceed** — pass the gate.
- **refocus** — a tangent detected: name it, drop it or park it in the SDD, re-run the check.
- **defer** — a decision was made too early: strike it, record it as deferred, continue.

## Tangent test

Before any non-trivial action, one question: *"Which line of the written problem does this serve?"* No line → it's a tangent. Report it; don't chase it.

Never edit an anchor, self-approve a waiver, or count a failed quality run as a cheap success.

---

_Provenance: write-first and assume-failure echo Kidlin's and Murphy's laws; decide-late is lean's "decide as late as possible." The guards are named for the behavior, not the attribution._
