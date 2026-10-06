# ADLC5 dogfood

Validate autonomous delivery in a **consumer app repo** (not the adlc5 framework clone).

## Setup

```bash
cd /path/to/your-app
/path/to/adlc5/scripts/init-workspace.sh --project .
/path/to/adlc5/scripts/install.sh --platform cursor
```

## Standard feature profile

```bash
cp /path/to/adlc5/templates/policies-small-feature.yaml.example .adlc5/demo-feature/policies.yaml
/path/to/adlc5/scripts/init-feature.sh --feature demo-feature --scope increment --interaction autonomous
```

Use `policies-tiny.yaml.example` only for bounded low-risk changes and
`policies-high-risk.yaml.example` for auth, money, secrets, destructive work,
migrations, concurrency, public compatibility, or disputed requirements.

## Autopilot smoke

```bash
/path/to/adlc5/scripts/pilot-autopilot.sh --feature demo-feature --workspace .
```

Expect JSON with `action: spawn|advance|halt|done`.

## Kill-switch tuning

Default tripwire: `consecutive_failure_tripwire: 3` in policies.

For dogfood, lower `wall_clock_cap_minutes` to 30 and `max_iterations` to 40 to fail fast.

Create stop file to halt:

```bash
touch .adlc5/demo-feature/STOP
```

## Local navigator

```bash
/path/to/adlc5/scripts/runner/dispatch.sh --feature demo-feature --max-iter 10
```

Without a host adapter, `spawn`, `advance`, and `heal` return
`dispatch: needs_executor`; the command does not pretend to execute an agent or
spin until `max_iter`. A host adapter performs the action, updates state, and
invokes the navigator again.

## Success criteria

- Unified state resumes without chat history
- `budget-check.py` stays within `context_budget_tokens`
- `pr-ready` gate enforces `quality_gates` under autonomous mode
- Evidence log at `.adlc5/{feature}/evidence/events.jsonl`
