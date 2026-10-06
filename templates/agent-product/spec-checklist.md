# Agent product spec checklist — {feature-name}

**Product type:** agent · **Concepts:** [07-ai-agent-orchestration.md](../../shared/docs/knowledge-base/07-ai-agent-orchestration.md)

## L3 orchestration pattern (pick one)

- [ ] Single agent
- [ ] Supervisor + workers
- [ ] Pipeline
- [ ] Council / ensemble
- [ ] Other: ___

## Runtime (L3 — framework-agnostic)

| Item | Decision |
|------|----------|
| State store | session / thread / durable workflow |
| Tools (list) | |
| Memory scope | |
| Max steps / budget | |

## Human-in-the-loop

| Gate | Trigger | Action |
|------|---------|--------|
| | | |

## Evaluation (§6)

| Metric | Threshold | Eval set path |
|--------|-----------|---------------|
| | | |

Baseline run id / date: ___

## Release (§7 — abstract)

| Item | Decision |
|------|----------|
| Artifact per version | |
| Runtime attachment | |
| Registration / discovery | |
| Rollback | |

## Observability (§8)

| Signal | Required fields |
|--------|-----------------|
| Trace | |
| Logs | correlation id: yes/no |

### Token/cost collection (§8 pattern)

Not a budget number in a cell — a per-call ledger the budget check actually reads. See [core/guides/agent-orchestration.md](../../core/guides/agent-orchestration.md) "Token/cost observability" row for ADLC5's own worked reference (`usage-ledger.py`).

| Item | Decision |
|------|----------|
| Per-call record fields | model id, tier, tokens by type, session/thread id, step |
| Session rollup | where computed / read from |
| Fleet rollup (cross-session) | yes/no — mechanism |
| Budget threshold | |
| Enforcement on breach | warn / block next call / kill-switch |

## ADLC5 delivery

| Stage | Owner skill | Done when |
|-------|-------------|-----------|
| Specify | @adlc5-specify / @prt | requirements and acceptance are explicit |
| Plan | @adlc5-plan | architecture, contracts, operations, and critique complete |
| Tasks | @adlc5-tasks | code spec lists eval tests **before** implementation |
| Implement | @adlc5-implement | build, independent verify, integration, QA, and PR gates pass |

## Scaffold (greenfield only)

- [ ] `scaffold-manifest.md` exists
- [ ] Story 0 uses registry `official_scaffold` (not hand `mkdir`)

**Stack adapter (if any):** ___ (registry id: ___)
