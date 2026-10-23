# Golden harness qualification

Implementation and contract tests establish boundary behavior. Live host
qualification is scoped in [live-host results](live-host-qualification.md); the matched comparison is unexecuted. No superiority, savings,
enterprise reliability or production qualification claim follows from this change.

## Frozen workload and arms

Keep the original six cases and their acceptance script unchanged. The
`--suite extended` option adds six cases from
`templates/evaluation/qualification-cases.json`, producing twelve workloads.
They cover repository-discoverable intent, contradictory requirements,
tenant authorization, migration recovery, retries/duplicates and changed intent
with interruption/resume. Original cases remain available with the default
`--suite pilot`; the extended suite pins the pre-change baseline to `3308e85`.

Each arm gets the same task, initial consumer commit, external acceptance and
regression scripts, tool access, host/model settings, user availability and budget:

1. Direct coding agent.
2. Frozen ADLC5 baseline.
3. Candidate ADLC5, identified by revision, dirty state and content digest.
4. Pinned Spec Kit checkout, materialized from an exact forty-character commit.

Prepare one fresh run without starting a model:

```bash
python3 scripts/evaluation/run-case.py prepare --suite extended \
  --case tenant-export --arm candidate --host HOST --model MODEL \
  --directory /tmp/qualification-run
```

The Spec Kit arm additionally requires `--speckit-path /path/to/checkout` and
`--speckit-revision COMMIT_SHA`. At execution time inspect its pinned official
documentation and use its actual workflow. Do not impose ADLC5 internal gates
on direct or Spec Kit arms. The adapter's synthetic checkout test validates
pinning and dispatch only; it is not a real Spec Kit run.

Framework digests and external oracle hashes are checked during collection.
Case tasks and budgets are frozen. Keep stakeholder scripts and acceptance
oracles outside the worker's writable consumer repo. The human evaluator owns
`STAKEHOLDER.json`: do not expose it or its answers in worker context. Supply
the scripted answer only when the agent reaches the seeded product decision.
For changed-export, interrupt after initial verification, provide the changed
policy and restart in a fresh session. Observe retention, stale review rejection,
new denied-path checks and a fresh independent review. Final behavioral tests
alone do not prove that this interaction happened.

## Review, accounting and observations

All arms need the same independent diff review. Record
`independent-review.json` with actual coder and verifier session IDs (different),
passing disposition, empty blocking findings and `patch_sha256` from the
collector's `framework_digest(consumer)` helper. That digest covers the current
consumer inputs; changing them invalidates the review. Record maintainability,
regression and security findings externally using the same rubric for each arm.
Internal ADLC5 gates are a separate `process_conformance` field; they cannot
determine the competing arms' external quality outcome.

Populate `observations.json` from actual evidence. Question adjudication uses
`question_review: {reviewer, unnecessary_questions, missed_consequential_questions,
lost_answers, repeated_setup_questions}`. Counts are nonnegative integers and
remain null before independent adjudication. A repository-answerable question
is unnecessary; silently choosing a seeded business tradeoff is a missed
consequential question. Retained answers are reused after restart without a
duplicate setup question. Ambiguous judgments require human adjudication.

Record actual active time and human waiting time separately as `active_seconds`
and `human_wait_seconds`; leave unavailable values null. Collection reports total
elapsed time from preparation, including idle time. Preserve failures, repairs,
interventions, interrupted runs, missing accounting and failed-run spend. Do not
equate cached provider input with fresh billed tokens or use missing cost as zero.
Record per-call model/host versions, permissions and cost source. Avoid exporting
raw user answers, prompts, secrets or consumer data in public results.

Collection runs independent checks; it does not implement a feature:

```bash
python3 scripts/evaluation/run-case.py collect --directory /tmp/qualification-run
```

Escaped defects remain unknown until the defined observation window completes.
Safe stops count as decision safety, not completed delivery. Report external
quality independently from accounting completeness. Freeze review rubrics before
runs, blind reviewers to the arm where feasible, and never use the delivery model
as the sole quality judge.

## Execution and release boundary

First qualify two real end-to-end host cases, including permission separation
and interruption/resume, on one available host. Stop on authorization bypass,
data loss, stale evidence acceptance or broken resume. Then qualify the other
advertised hosts; shared contract/package tests do not establish host parity.

The full campaign is twelve cases × four arms × three fresh repetitions: 144
planned runs. Set campaign and per-run spend/time limits before execution.
Use fresh directories and sessions; never recycle a successful patch between
arms. Record completed, failed, timed-out, interrupted and unexecuted runs.
Report per-case paired differences and uncertainty intervals, retaining workload
correlation across repetitions. Expand workloads if uncertainty prevents the
intended claim; obtain independent analysis review before publishing comparisons.

Release screening requires passing boundary tests, no critical regression,
every seeded consequential decision resolved before affected implementation or
a correct safe stop, retained answers across restart, and no stale evidence
accepted. Investigate every paired quality regression against the baseline.
Cost/time comparisons apply only to comparable quality outcomes. This descriptive
screen is not statistical proof of non-inferiority.

The owner subsequently authorized live host qualification and retained the
comparative campaign as the final deferred step. Bounded native feasibility runs
have now executed; see [results and limits](live-host-qualification.md).
All 144 comparative campaign runs remain unexecuted. No deployment, installation
or publication is included.
