# ADLC5 evaluation contract

ADLC5 optimizes cost only after independently checkable quality holds. It does not combine quality and cost into one score.

## Task classes

| Class | Typical scope | Minimum route |
|---|---|---|
| Tiny | Bounded, low-risk change with clear acceptance evidence | Compact Specify/Plan/Tasks record → Implement → tests → diff review |
| Standard | Ordinary brownfield feature | Specify → brief Plan → Tasks → Implement → Verify → PR readiness |
| High-risk | Auth, money, secrets, destructive operations, schema migration, concurrency, public compatibility, or disputed requirements | Full Plan + anchored evidence + independent Verify + QA/security + human approval |

## Frozen case contract

Each evaluation case starts from a fixed repository revision and records:

- task class and unchanged task text,
- consumer-owned acceptance command,
- existing regression command,
- acceptance evidence files and SHA-256 digests where applicable,
- model/provider and execution policy,
- wall-clock and cost budget.

Exclude cases without an independent acceptance command. Do not substitute an LLM quality score.

## Compared variants

Run every case from equivalent disposable worktrees with fresh model sessions:

1. direct coding agent,
2. frozen ADLC5 baseline,
3. candidate tiny, standard, or high-risk policy.

Private prompts, repository paths, and raw results stay local. Only product-agnostic schemas and anonymized aggregates belong in this repository.

## Outcomes

A run is successful only when both frozen commands pass, no acceptance anchor
changed, no human rejected it, and the recorded escaped-defect count is zero.
Outcome records must explicitly include `anchors_passed`, `regression_passed`,
`quality_gates_passed`, `anchor_changed`, `rework`, `human_rejected`, and a
non-null nonnegative integer `escaped_defects`; `rework` is also a nonnegative
integer count and boolean fields must be actual JSON booleans. Missing or unknown fields fail the quality floor rather than defaulting favorably. `quality_gates_passed` means every
gate required by the selected profile passed, including QA/security for
high-risk work.

Record:

- acceptance and regression command results,
- provider cost when available; otherwise token counts and their source,
- elapsed time,
- retries and rework,
- human rejection or intervention,
- revert/rollback and escaped defects,
- diff size,
- verifier findings that changed the patch.

Use the same `run_id` and `node_id` in telemetry and usage. A caught defect also
needs a stable `finding_id`, so retries can deduplicate one finding without
collapsing distinct defects. Duplicate outcome records for one run are
ambiguous and excluded from evaluation.

A successful outcome also requires at least one economically valid usage record
whose `run_id` and `node_id` match telemetry. A record must report token or cost
accounting; token, attempt, and cost values must be finite and non-negative.
Invalid records are excluded and disqualify that run from the successful cohort.
An explicit `cost_usd: 0` is authoritative and must not fall back to an estimate.

Minimize `tokens`/`cost_usd` only among successful runs; failed-run spend is
reported separately as `failed_tokens`/`failed_cost_usd`. Reject policies that
lower the frozen-anchor pass rate, hide anchor changes, or increase unresolved
rework.

## Reproducible six-case handoff

The public case bank is `templates/evaluation/cases.json`; the stdlib consumer is
`dogfood/consumer/`. `scripts/evaluation/run-case.py prepare` creates an isolated
Git consumer with a deterministic starting commit, frozen independent checks,
host/model metadata, budget, a manifest integrity hash, and a fresh-session handoff. Baseline preparations
extract the framework revision recorded in `templates/evaluation/cases.json` into the run; candidate preparations record
HEAD, whether local changes exist, and a content fingerprint. Freeze the candidate checkout throughout
an experiment. No host-agent executor or subscription is needed to test setup.

For a golden-state comparison, pass `--baseline-revision` with the full frozen
ADLC5 commit SHA. Run separate candidate arms with
`--candidate-routing same-model` and `--candidate-routing tiered`. This labels
the frozen manifest and output cohort. The evaluator pins the tier configuration
and verifies observed model receipts before including a run in that comparison.
The defaults keep the original case banks and comparison labels.

Run every case under `direct`, `baseline`, and `candidate` with new host sessions
and distinct directories. Record the number of actual repetitions, not planned
repetitions. Acceptance/regression commands and observation windows are identical
across arms. Cases intentionally begin with failing acceptance checks. They cover
label preservation, missing quantities, normalized search, CSV quoting, resolved
path containment, and atomic replacement with failure preservation.

After actual delivery/review, populate the run's `observations.json` with real
telemetry and usage entries (matching run/node IDs). Include accounting source and
model identities. High-risk approval is a real human step, not fixture data.
`collect` executes consumer checks and calls the existing scorer. Its null
escaped-defect value remains null until the frozen observation window is recorded
as complete. Missing accounting is reported unavailable, including null spend
buckets; it cannot enter the successful cohort. A report from preparation alone
is a fixture smoke test, never a live agent comparison.

The six-case bank tests the evaluation procedure; it is not statistical proof
of coding quality. Contract tests and scripted demos do not establish live
agent reliability or cost savings. Comparative quality, cost, and newcomer
usability remain unqualified; no live pass-rate or cost advantage is claimed.

The collector executes actual `pr-ready` and anchor gates for framework arms; a
manual observation cannot assert their pass. Direct-arm review needs a local
independent-review record with distinct execution identities and no blocking
findings. Integrity protects against accidental changes through this procedure,
not malicious edits to writable files. `demo-consumer.py` exercises real init,
check evidence, a valid transition, completion rejection and process restoration
without synthesizing review or approval; it is labeled a scripted contract demo.

## Campaign PR acceptance

For a campaign fixture that will be delivered to GitHub, prepare with
`--pr-repository OWNER/REPO` and one `--required-check 'Exact check name'`
per job required by the frozen campaign. Use a disposable repository approved
for publishing the fixture. The same check list and case budget apply to every
paired arm. Use `--wall-clock-minutes` to freeze a campaign-specific budget. Before doing any host work, record `started_at` in
`observations.json` as an ISO 8601 timestamp with an offset. Collect every
started run, including interrupted runs and runs with missing evidence.

In addition to the existing independent review fields, the reviewer records
`pr_url`, `head_sha`, and `reviewed_at` in `independent-review.json`.
The operator captures the current PR and the matching check runs from GitHub,
then saves the evidence in `remote-pr.json`. The receipt has this shape:

```json
{
  "url": "https://github.com/OWNER/REPO/pull/123",
  "head_sha": "<observed PR head SHA>",
  "observed_at": "<timestamp when the PR and checks were checked>",
  "acceptance": {
    "head_sha": "<independently tested head SHA>",
    "conclusion": "success",
    "completed_at": "<timestamp of external acceptance completion>"
  },
  "regression": {
    "head_sha": "<independently tested head SHA>",
    "conclusion": "success",
    "completed_at": "<timestamp of external regression completion>"
  },
  "checks": {
    "Exact check name": {
      "head_sha": "<observed check head SHA>",
      "conclusion": "success",
      "completed_at": "<timestamp of the successful check>"
    }
  }
}
```

Use timestamps with offsets. The collector validates operator-captured evidence
locally. Verify the receipts directly in GitHub before using them as release
evidence. Capture a fresh receipt if the PR head changes.
The collector checks the receipt against the clean local evaluation checkout,
the independent review, rerun frozen acceptance and regression checks, and
the recorded human disposition. It uses the latest independent review, remote
CI, acceptance, or regression completion as the acceptance time. Internal
ADLC5 process conformance is reported separately. The wall-clock deadline is
the actual start plus the frozen case budget. A paired comparison reports
accepted by deadline divided by started, counts late acceptance separately,
and keeps missing acceptance evidence in the started denominator. Runs with
an unavailable start are counted separately and leave the cohort rate unavailable. Aggregate outcomes from a single
frozen campaign at a time.

Record observed `active_seconds`, `human_wait_seconds`, `quota_wait_seconds`,
and `ci_wait_seconds` independently. Use null when a duration is unknown.
Treat overlapping intervals as overlapping when reporting these measurements.
The elapsed wall clock continues during every wait. The original fixture
quality and cost outcomes retain their observation and accounting requirements.

Campaign spend per accepted feature includes spend from all started runs in
each cohort, including failed and late runs. Its denominator counts all
accepted features, including late acceptance. The deadline rate remains a
separate measure. For each started run, the operator can add
`"campaign_spend_attestation": {"complete": true, "basis": "provider billed USD"}`
to `observations.json` once the usage entries account for the full run. Use the
same observed accounting basis throughout the campaign. Each usage record must
have an explicit numeric `cost_usd`, matching run/node telemetry, and a unique
node/attempt combination within its run. Use explicit zero only when observed.
Missing attestations, estimated-only costs, conflicting or duplicate records,
mixed bases, and ambiguous starts leave the metric unavailable.
