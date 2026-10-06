# Evidence-backed completion

Use the existing `scripts/adlc5` façade (or its thin MCP tools) in the consumer
workspace. Dedicated operations own progression and results; `state set` edits
metadata. Legacy features remain readable but need current evidence before earning
completion. These commands enforce supported workflows, not security against an
actor who can rewrite local files or Git refs.

## Before building

Record `.adlc5/FEATURE/risk.json`:

```json
{"categories": [], "uncertain": false, "rationale": "Bounded local change with no trust/data/compatibility impact"}
```

Known categories: `auth`, `money`, `secrets`, `migration`, `concurrency`,
`destructive`, `public_compatibility`, `disputed_requirements`. Any category or
uncertainty needs `high_risk`, including its mandatory human PR approval. This is explicit judgment, not
automatic risk detection. Reassess when scope changes.

Tiny work writes `change.md` (reuse, boundary, acceptance, risks; declared file lists) and a minimal
spec handoff. Standard work writes `design/plan.md` and machine-checkable story
specs. High-risk/full work keeps detailed design and independent critique.
Initialize canonical acceptance entries before locking anchors.

```bash
/path/to/adlc5/scripts/adlc5 anchors lock --feature FEATURE
/path/to/adlc5/scripts/adlc5 pilot --feature FEATURE
/path/to/adlc5/scripts/adlc5 transition NEXT_STEP --feature FEATURE
```

Use the next enabled step from `pilot`; the kernel rejects jumps. For example,
standard handoff advances to `plan-4-design-discovery`, then `tasks-1-stories`.

## Build, checks and review

At `implement-1-build`, record the implemented story IDs in a JSON file:

```json
{"story_ids": ["US-001"]}
```

```bash
/path/to/adlc5/scripts/adlc5 evidence build --feature FEATURE --file build.json
```

Declare named commands in `.adlc5/FEATURE/evidence/checks.json`. Configure the
consumer's real acceptance, regression and any required lint/integration checks;
do not replace these with commands that merely inspect lifecycle paperwork.
Profiles that retain integration require a named `integration` command. Selected
quality thresholds require named `lint`, `coverage`, or `complexity` commands whose
exit codes enforce those thresholds. Required checks are run once per evidence
invocation; freshness gates reuse those results. Each check accepts an optional
positive integer `timeout_seconds` (default 300); increase it for longer suites.
Changes to check configuration or the active feature/fallback policy invalidate evidence.

```json
[
  {"id": "acceptance", "command": "python3 acceptance.py", "required": true},
  {"id": "regression", "command": "python3 regression.py", "required": true}
]
```

```bash
/path/to/adlc5/scripts/adlc5 evidence check --feature FEATURE
```

This runs commands, records their working directories, exit results and logs, and
checks that inputs did not change during execution. Unsupported required commands
block completion. Standard/high-risk specs remain required even when commands pass. High-risk also
requires a named `security` command that tests the applicable trust/data boundary
or runs the selected scanner; a QA `CLEARED` marker alone is insufficient.

Have the actual reviewer inspect the patch against acceptance and record:

```json
{
  "coder_session_id": "actual-coder-session",
  "verifier_session_id": "actual-reviewer-session",
  "coder_model_id": "actual-coder-model",
  "verifier_model_id": "actual-reviewer-model",
  "disposition": "pass",
  "blocking_findings": []
}
```

```bash
/path/to/adlc5/scripts/adlc5 evidence review --feature FEATURE --file review.json
```

Standard/high-risk need distinct sessions. Distinct models are enforced when the
policy requests them. A different model alone does not establish quality. Tiny
still needs a diff review under its lighter policy. Use `reject` and record blocking
findings when appropriate; do not fabricate execution identities or passing review.

## Complete or recover

Advance each enabled implementation step with `transition`. At `implement-5-pr`,
complete with `transition completed` after the required gates pass. Record a PR URL
only when a PR exists. If policy requires human approval, obtain the user's actual
response and submit `{"type":"pr_approval","approved_by":"user"}` via
`evidence approve --file approval.json`; agents cannot infer
approval from elapsed time or successful tests.

Completion evidence includes current patch, acceptance and configuration inputs.
Edits invalidate affected records; rerun checks/review after relevant changes.
Outputs and summaries are excluded so recording results does not invalidate itself.
Check limits and file exclusions in `scripts/lib/completion_evidence.py`.

For recovery, `state repair --patch JSON --reason TEXT` writes an audit record.
It may reopen/reset progress; it cannot manufacture verified/completed results or
human approval. Reverification is required. Resume a new session with state, the
spec/plan, and `pilot` output; previous chat is not a source of completion evidence.

## Context limits

`adlc5 pack` assembles required story/acceptance/spec and available repository rules.
Missing required content or an over-budget pack blocks the handoff; required content
is never silently trimmed. `budget-check.py --handoff --paths PACK` estimates the
supplied text as characters/4. Hidden host prompts and subsequent source reads are
unknown overhead; this is not a hard whole-session token cap.

Approval records accept an explicit `decision: approve | reject`; the latest
record for the current inputs governs readiness. Negative/unknown payload fields
cannot silently become approval. Scoped `deploy_approval`, `anchor_relock_approval`
and `verifier_waiver` records use the same operation, with their required environment,
digest/reason fields. Deployment still requires completed delivery and an actual
published PR; a verifier waiver does not replace mandatory current checks/review.
