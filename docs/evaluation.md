# ADLC5 evaluation contract

ADLC5 optimizes cost only after independently checkable quality holds. It does not combine quality and cost into one score.

## Task classes

| Class | Typical scope | Minimum route |
|---|---|---|
| Tiny | Bounded, low-risk change with clear acceptance evidence | Spec confirmation → implement → tests → diff review |
| Standard | Ordinary brownfield feature | Specify → Tasks → Implement → Verify → PR readiness |
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
2. current standard ADLC5,
3. candidate tiny, standard, or high-risk policy.

Private prompts, repository paths, and raw results stay local. Only product-agnostic schemas and anonymized aggregates belong in this repository.

## Outcomes

A run is successful only when both frozen commands pass, no acceptance anchor
changed, no human rejected it, and the recorded escaped-defect count is zero.
Outcome records must explicitly include `anchors_passed`, `regression_passed`,
`quality_gates_passed`, `anchor_changed`, `rework`, `human_rejected`, and a
non-null integer `escaped_defects`; missing or unknown fields fail the quality
floor rather than defaulting favorably. `quality_gates_passed` means every
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

## Pilot

Start with two cases per class. This six-case pilot is a smoke comparison, not statistical proof. Keep mandatory nodes that catch a real defect class; make repeatedly idle low-risk nodes conditional; downgrade a model only when the quality floor remains intact.

## Formats and storage

| Data | Canonical format | Storage |
|---|---|---|
| Human requirements, plans, code specs, skills | YAML frontmatter + Markdown | Git-backed files |
| Mutable lifecycle state | Schema-validated JSON | Local filesystem with atomic replace |
| Transitions, evidence, telemetry, usage | JSONL | Feature-local filesystem; archive with feature |
| Generated context packs | Markdown | Disposable feature-local files |
| Binary source documents | Original + derived Markdown + source hash | Feature-local inputs; original remains authoritative |
| Current fleet analytics | JSONL + offline summaries | Local/archive storage |
| Large analytical workloads | Parquet export, only after measured need | Analytical/object storage |

Do not add Redis, tmpfs, Protobuf, Parquet/Lance, vector storage, or a graph database until profiling identifies the current representation as the bottleneck. Microsoft MarkItDown may be added later as an optional local-only Specify intake adapter when a frozen binary-document case justifies it; it is not a runtime dependency.
