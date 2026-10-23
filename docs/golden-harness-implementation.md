# Golden harness implementation review map

This branch implements the planned harness changes using Codex directly. It
does not run ADLC5's lifecycle on its own distribution. The code and contract
coverage below are distinct from live outcome qualification.

| Plan increment | Implementation | Evidence boundary |
|---|---|---|
| 0: Baseline failures | Frozen readiness regressions plus existing six-case pilot | Deterministic reproduction; not live frequency |
| 1: Explicit readiness | Shared validator, CLI/MCP, canonical gates and transitions | Clarity score cannot certify intent; stale/malformed evidence fails |
| 2: Investigation/questions | Investigation guidance, structured worker questions, intent-bound answers and resume recovery | Product answers cannot grant command permission; legacy reads retained |
| 3: Change/convergence | Requirement/decision/story/acceptance mapping, conservative impact, review history, existing anchors/rework budgets | Unknown mappings block; changed intent requires new review and evidence |
| 4: Proportionate delivery | Canonical profile routing, operational applicability/evidence, coder constraints, conformance review | Applicable missing evidence blocks completion; readiness labels remain separate |
| 5: Qualification tooling | Extended twelve-case suite, four arms including pinned Spec Kit, shared external review and separate process conformance | Bounded native qualification executed; see live-host results. All 144 comparative campaign runs remain deferred |

## Review order

1. `scripts/lib/requirements_readiness.py`, then its CLI/MCP and gate/transition
   callers: inspect freshness, trust boundaries, history and delivery validation.
2. `scripts/runner/questions.py`, `answer.py`, and `run.py`: inspect product versus
   permission separation, idempotence, stale inputs, locking and crash recovery.
3. Context packs, profiles and stage/persona guidance: inspect required constraints
   and the compact tiny route; auxiliary work needs a concrete reason.
4. Evaluation runner, extended fixtures and independent acceptance: inspect pinned
   inputs, oracle isolation, shared quality criteria, missing accounting and
   separation of scripted checks from actual host runs.
5. Regression tests and existing tiny/standard/high-risk delivery tests.

## Compatibility and limits

Active legacy features need an explicit review before protected progression;
historical completed records stay readable. Legacy text questions remain readable.
Unbound historical answers are context, never current authorization. New answers
are tied to intent or permission inputs. Use the compatible kernel after migration;
an older installed kernel does not acquire these checks automatically.

Reviews, identities, classifications and evidence files are local attestations.
Validation cannot discover every omitted business requirement, authenticate a
human against an arbitrary filesystem writer, or prove production quality from
coverage labels. Actual semantic review, independent acceptance and live
qualification remain necessary. First-release impact analysis invalidates feature
readiness conservatively; selective dependency caching remains deliberately
deferred until measured rerun cost justifies it.

No deployment, installation, paid campaign or public comparison is part of this
implementation. See [qualification protocol](golden-harness-qualification.md)
and [record contract](requirements-readiness.md). The owner subsequently authorized
bounded live host qualification; [results](live-host-qualification.md) supersede
the earlier unexecuted host status, not the deferred comparative campaign.
