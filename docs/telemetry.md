# ADLC5 feature telemetry

Optional **opt-in** observability for autonomous / pilot runs. Default HITL flows do not require telemetry.

## Location

```
.adlc5/{feature}/telemetry/events.jsonl
```

One JSON object per line (JSONL). Created on first `telemetry_emit` from gate scripts under `scripts/`.

## Event schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ts` | string (ISO8601 UTC) | yes | Event timestamp |
| `event` | string | yes | `script.start`, `script.end`, `checkpoint`, `stage_picker`, `gate_fail`, `phase_advance`, `policy_decision` |
| `script` | string | yes | Basename, e.g. `check-gates.py` |
| `feature` | string | yes | Feature kebab-case name |
| `phase` | string | no | Canonical v3 `current_step` when known; legacy delivery `current_phase` is normalized on read |
| `status` | string | yes | `ok`, `pass`, `fail`, `warn`, `blocked`, `skipped`, etc. |
| `details` | object | yes | Script-specific payload (gate result, test counts, …) |
| `run_id` | string | no | Stable ID shared with usage and external outcome records |
| `node_id` | string | no | Work-graph node, such as `build` or `verify` |
| `parent_node_ids` | string[] | no | Immediate lineage edges |
| `attempt` | integer | no | One-based node attempt number |
| `outcome` | string | no | Observable result, such as `defect_caught` |
| `finding_id` | string | no | Stable finding identity; required when `outcome=defect_caught` |

### Example lines

```json
{"ts":"2026-05-23T12:00:00Z","event":"script.start","script":"run-tests.sh","feature":"visual-qa-tools","phase":"implement-1-build","status":"ok","details":{}}
{"ts":"2026-05-23T12:00:45Z","event":"script.end","script":"run-tests.sh","feature":"visual-qa-tools","phase":"implement-1-build","status":"pass","details":{"runner":"pytest","status":"pass","passed":42,"failed":0}}
```

## Emitting events

**Pilot / navigator events:**

| Event | Emitter | When |
|-------|---------|------|
| `stage_picker` | `pilot.sh` | `resume_from` jump applied |
| `gate_fail` | `pilot.sh` | Deterministic gate `fail` before spawn/heal |

Gate scripts source `scripts/lib/telemetry.sh` and call:

```bash
telemetry_emit "$FEATURE" "script.start" "my-script.sh" "ok" "$PHASE" '{}'
telemetry_emit "$FEATURE" "script.end" "my-script.sh" "$STATUS" "$PHASE" "$DETAILS_JSON"
```

Set `ADLC5_WORKSPACE` to the repo root when not running from project root.
Set optional `ADLC5_RUN_ID`, `ADLC5_NODE_ID`, `ADLC5_PARENT_NODE_IDS`
(JSON array), `ADLC5_ATTEMPT`, `ADLC5_OUTCOME`, and `ADLC5_FINDING_ID` to
correlate an event with usage and outcome records.

## Outcome evaluation

Join telemetry, `memory/usage-ledger.jsonl`, and a consumer-owned outcome JSONL:

```bash
./scripts/evaluate-runs.py \
  --telemetry .adlc5/FEATURE/telemetry/events.jsonl \
  --usage .adlc5/FEATURE/memory/usage-ledger.jsonl \
  --outcomes /path/to/outcomes.jsonl
```

The report separates the frozen quality floor from cost. It never emits a
blended quality score. See [evaluation.md](evaluation.md).

## Viewing

```bash
./scripts/tail-telemetry.sh --feature visual-qa-tools -n 50
./scripts/tail-telemetry.sh --feature visual-qa-tools -f
```

## Retention

No rotation is performed by ADLC5. Consumer projects may archive or truncate `events.jsonl` per ops policy.

## Optional minimized sharing

Local event files remain local. They can contain feature names, run IDs, script
details and test/command output, so they are **never uploaded verbatim**. The
separate exporter reads those files locally and emits fixed event/status bucket
counts since the last successfully sent batch. A local cursor (which may contain
workspace feature-directory names) stays in `.adlc5/telemetry` and is never
transmitted. It sends no prompt, source, command, output, repository or feature
label, timestamp, run ID, usage record, or persistent user identifier. It does
not calculate savings or accuracy. Use [the controlled evaluator](evaluation.md)
for measured comparisons; quality gates remain ahead of cost claims.

Sharing is disabled by default per workspace. Preview is local and makes no
network request. Opt-in displays the payload and requires typing `yes`; opting
in does not upload anything. Sending is a separate command and asks again. The
endpoint has no built-in default; set `ADLC5_TELEMETRY_ENDPOINT` to an
operator-managed HTTPS intake URL only after deploying and reviewing it:

```bash
./scripts/adlc5 telemetry preview --workspace .
./scripts/adlc5 telemetry opt-in --workspace .
ADLC5_TELEMETRY_ENDPOINT=https://telemetry.example.com \
  ./scripts/adlc5 telemetry send --workspace .
./scripts/adlc5 telemetry opt-out --workspace .
```

The exporter queues at most 10 aggregate submissions locally and tries the
oldest submission at most twice per explicit `send`. Failures retain that
submission for a later manual retry; there is no background retry. Opt-out
deletes consent, the local queue, and the sharing cursor, but does not delete
the existing local event files or records already received by an endpoint.

Structured and free-text feedback uses a separate endpoint and requires an
explicit `feedback` submission. Optional free text is separately previewed and
limited to 1,000 characters. Do not include secrets, personal data, prompts or
source code. Free text is not anonymous; it is stored separately from aggregate
telemetry.

The reference receiver is in [`telemetry-intake/`](../telemetry-intake/README.md).
It validates an allowlisted schema, limits requests to 4 KiB and 3 per minute
per transport IP, uses only the IP for Cloudflare's transient rate-limit key,
and does not store that IP or log request headers/body. Cloudflare still
processes connection metadata, including source IP, so this is minimized
telemetry, not a promise of anonymity. The reference receiver applies a 90-day
retention policy. Operators must also review Cloudflare account/zone logging and
their privacy notice before enabling a public endpoint.

Pulse integration is a follow-up: only controlled evaluator reports with
comparable baseline runs and accepted outcomes can support measured savings or
quality displays. Aggregate operational telemetry alone cannot establish either.
