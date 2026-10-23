# Requirements readiness

ADLC5 requires current, reviewable intent before protected progression. A clarity
score is document lint, not evidence that the requirement is understood. The same
record carries decisions, operational applicability, story traceability and intent
conformance. Live comparative qualification remains a separate measured activity.

## Supported workflow

Write the feature's behavioral intent in `spec-handoff.md`. Tiny features retain
their existing compact `change.md` too; no full design tree is required. Record
`risk.json` and the selected policies first. Then prepare a draft:

```bash
./scripts/adlc5 readiness prepare --feature example --workspace /path/to/consumer > /tmp/example-review.json
```

Preparation snapshots required sources and effective scope/policy. It does not
approve anything or write lifecycle state. Read the actual intent, assess behavior,
contradictions, negative cases and assumptions, and fill in the draft. An example
of the sections to supply (the source manifest and digest come from prepare):

```json
{
  "requirements": [
    {
      "id": "FR-1",
      "source": ".adlc5/example/spec-handoff.md",
      "acceptance": ["Given a mixed-case label with whitespace, trimming preserves its spelling."]
    }
  ],
  "decisions": [],
  "review": {
    "author_session_id": "actual-author-session",
    "reviewer_session_id": "actual-review-session",
    "disposition": "pass",
    "coverage": ["behavior", "contradictions", "negative_cases", "assumptions"],
    "findings": []
  }
}
```

Use actual session identities. High-risk intent requires a different reviewer
session; standard/tiny permit the author's own focused assessment. Never invent
independence. Register only a review that actually happened:

```bash
./scripts/adlc5 readiness record --feature example --workspace /path/to/consumer --file /tmp/example-review.json
./scripts/adlc5 readiness check --feature example --workspace /path/to/consumer
```

The thin MCP equivalent is `adlc5_readiness`, with `action` equal to `prepare`,
`record`, `check`, `delivery`, or `impact`, and the same `feature`, `workspace`, and optional `file`.
For additional intent documents, supply `sources` as an array of workspace-relative paths.
Relative request filenames resolve against the consumer workspace. Failed record
validation preserves the previous artifact. `check` returns exit 2 when blocked;
normal gate and transition failure contracts remain unchanged.

## Version 1 record contract

`.adlc5/FEATURE/requirements-readiness.json` contains these top-level keys:

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1`, never a boolean |
| `feature` | Canonical feature identity |
| `sources` | Nonempty array of `{path, sha256}` records; unique contained file paths |
| `intent_sha256` | Hash of the source manifest, effective policies, scope and scale NFR metadata |
| `requirements` | Nonempty array of unique `{id, source, acceptance}` records; nonempty acceptance scenarios |
| `decisions` | Explicit decisions and assumptions; empty only if the review found none requiring a record |
| `review` | Actual identities, passing disposition, complete review coverage and disposed findings |
| `delivery` | Added during Plan (during Specify for tiny): operational obligations, story traceability and conformance review |

Mandatory sources include the feature handoff, tiny `change.md` when applicable,
`risk.json`, the selected policy file if present, and existing `AGENTS.md` and
tracked `.agents/{architecture,boundaries,commands}.yaml`. Prepare with `--source PATH`
for other load-bearing intent documents (repeat the option for multiple files).
The kernel snapshots their hashes; reference them in requirements. Supply those
additional sources again when preparing a new review revision.
Paths are relative to the workspace; missing files, traversal, symlink escapes,
duplicate fields/IDs, unknown fields and stale digests fail closed. The artifact
cannot refer to itself or mutable lifecycle state. Source manifests must preserve
the ordering used to compute the prepared digest.

Each decision contains `id`, nonempty `requirement_ids`, `disposition` (`inspect`,
`research`, `experiment`, `ask`, or `assume`), `status`, boolean `blocking`,
`rationale`, `evidence`, and `revisit_when`. Evidence entries are contained
`{path, sha256}` references. Investigation and user decisions require evidence;
for user decisions, cite the actual answer log. `ask` and `assume` also require
`answer: {source, text}`, with source `user` and `agent` respectively.

Only resolved decisions permit progression in version 1. Open/deferred decisions
remain blocked even if labeled nonblocking. Remove explicitly excluded work from
active intent instead of disguising it as resolved. A blocking decision cannot
be resolved by an agent assumption. Tagged assumptions require decision evidence.
Each finding is `{id, blocking, resolution}`; every finding needs a disposition.
Renaming a contradiction or recording an empty resolution cannot clear it.

The kernel checks structure, references, freshness, declared risk and review
disposition. It cannot determine that the reviewer discovered every omission or
that an arbitrary resolution is correct. IDs and coverage labels are attestations,
not a semantic oracle. Human answers and identities in local files are workflow
evidence, not authenticated signatures against an actor with filesystem access.

## Gates, freshness and legacy features

All schema-3 gate evaluations require current readiness, including Specify exit,
Plan, Tasks, Build, verification and PR readiness. All canonical transitions after
Specify, including transitions within a stage and repaired/reopened features,
validate it independently. Specify's internal discovery steps remain available
before a record exists so an incomplete feature can be investigated.

Intent review deliberately excludes code changes and lifecycle status. Effective
scope, scale NFR, risk, policy or declared intent changes require a new snapshot
and actual review. New applicable repository rules also stale the record.
The artifact remains part of the existing completion fingerprint, so changing it
invalidates old build/verification evidence. Required decisions also bind their
supporting evidence hashes. Story context packs include the current record for
coders and testers; a stale record cannot be packed. Existing legacy packs remain
readable, but cannot authorize protected progression without readiness evidence.
The runner serializes its own workers; atomic file
replacement prevents partial records. These local operations do not provide a
transaction against arbitrary concurrent filesystem writers.

Historical completed records stay readable. Existing active features need an
explicit assessment before their next protected transition; do not synthesize a
passing review from `clarity.score`. Old tools without this contract cannot safely
advance migrated features: keep the compatible kernel when resuming or recovering.
Never rewrite acceptance anchors or approval history to satisfy this check.

## Regression evidence and qualification

`scripts/tests/test-requirements-readiness.py` exercises placeholder padding,
malformed/duplicate inputs, stale scope/policy/sources, independent high-risk
review, metadata bypass, path containment, CLI/MCP parity and stage transitions.
Existing delivery tests use explicitly synthetic review fixtures to retain their
coverage of build/review/approval behavior; those fixtures are not live reviews.

The original failure reproduced on 5.0.1 was a spec with Functional Requirements,
Acceptance Criteria and Non-functional Requirements headings containing only
`TBD`, followed by `example validation 200`. The clarity heuristic awarded 100
and zero open items. The gate trusted the score. Current gates reject that intent
even when the legacy numeric result is 100. The heuristic keeps its old fields
for compatibility and now declares `heuristic: true`, `gate_authority: false`.

Contract tests establish these boundary behaviors only. They do not establish
improved live question quality, enterprise delivery reliability, lower cost or
superiority to another harness. Those require the later matched-run qualification.

## Delivery obligations and change handling

`adlc5 readiness delivery --feature NAME` prints a draft extending the current
valid review. It does not mark obligations satisfied. Fill and submit it with
`readiness record --file PATH` before leaving Plan; tiny work does so before Build.
The `delivery` object has `obligations`, `traceability`, `constraints`, and
`conformance` fields. Put mandatory authorization, compatibility, failure and
operational constraints in `constraints`, each `{requirement_ids, text, source}`
with source `{path, sha256}`. Coder and tester packs carry this record; do not hide
correctness constraints inside design documents unavailable to the coder.

Assess all eight operational categories: `authorization`, `migration`,
`compatibility`, `concurrency`, `performance`, `network`, `deployment`, and
`accessibility`. Each obligation is `{id, status, rationale, requirement_ids,
method, evidence}`. Use `pending`, `blocked`, `satisfied`, or `non_applicable`.
An applicable obligation needs affected requirement IDs and a concrete validation
method during planning; `satisfied` needs current `{path, sha256}` evidence.
Non-applicability needs an actual reason. Declared auth/secrets, migration,
concurrency and public-compatibility risks cannot mark their corresponding
obligation non-applicable. Unknown applicability remains pending or blocked.
PR readiness requires all applicable obligations satisfied. A local artifact must
say exactly what was checked; an unavailable production environment remains
unverified rather than being represented as a completed operational check.

Each `traceability` entry is `{story_id, requirement_ids, decision_ids,
acceptance_criteria}`. Before implementation, every non-integration story,
requirement and decision must be mapped; acceptance IDs must match the story's
code spec. Tiny work keeps acceptance in `change.md` and needs no story tree.
Story mappings establish applicability, not permission to rewrite frozen anchors.

Before completion, the verifier records `conformance: {reviewer_session_id,
coverage, requirements, evidence}`. Coverage is `missing`, `partial`,
`contradictory`, `unrequested`, and `constraints`; `requirements` names every
reviewed requirement and evidence hashes the actual verification report and
relevant implementation inputs. Resolve findings through existing corrective
tasks/rework and retry limits before recording conformance. Keep it null while
implementation is incomplete. This attestation complements independent diff
review and passing acceptance commands; it never replaces them.

`adlc5 readiness impact --feature NAME` compares the old review with current
intent. The first release conservatively marks all feature requirements and
stories affected. It preserves implementation and tests, requires reassessed
risk/decisions/obligations, and does not selectively reuse unknown dependencies.
Recording a replacement saves the previous record in content-addressed
`evidence/readiness-history/`. Original anchors, approvals and attempts remain
unchanged. After recording the reviewed revision, run current checks and obtain
a fresh independent review; old completion fingerprints cannot certify it.

## Runner decisions

Native structured-output hosts use a strict outer envelope with `attempt_id`,
`status`, `summary` and `payload_json`. The payload is an encoded JSON object
containing step-specific fields; it cannot override envelope fields. The runner
decodes and validates it before ingestion. Existing result objects stay readable.
Cursor's concatenated commentary transport may carry exactly one final fenced
JSON result; ambiguous or trailing results are rejected.

Workers emit a product question object with `decision_id`, `category: "product"`,
`text`, `rationale`, `recommendation`, `alternatives`, `requirement_ids`, and
`intent_sha256` from `readiness prepare`. Inspect repository evidence first,
research current facts or run a bounded experiment where useful, and ask for
business decisions the user owns. Record the chosen disposition in `decisions`.
Use one dependent question at a time, or at most two independent questions in
attended UI. Investigation uses the existing run/time/cost and retry limits.

`adlc5 answer ID --text TEXT` preserves free-form answers. Identical retries are
idempotent; conflicting answers and superseded intent are rejected. Answer
ingestion uses the runner lock and atomic writes, and retries repair a missing
journal entry after interruption, including recovery at resume. A product answer cannot add commands to an
allowlist. Legacy text questions remain readable and new text questions are
revision-bound. Permission denials retain their separate existing approval flow.
Resume archives superseded product questions and excludes their answers from
the current brief; new workers must reassess them. Already resolved decision IDs
cannot be asked again for the same intent revision.
Legacy unbound answers stay visible as historical context and cannot certify
current authorization. New permission questions bind the current completion
inputs; stale requests require current authorization. Answered questions are
archived after ingestion, so a consumed request cannot be replayed on restart.
