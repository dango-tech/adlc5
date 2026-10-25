# Agent governance — {feature-name}

**Copy to:** `.adlc5/{feature}/design/1d-agent-governance.md` at `plan-6-design-operations` when `state.product_type` is `agent`.
**Guide:** [core/guides/agent-governance.md](../../core/guides/agent-governance.md)

`plan-complete` fails while any `## ` section below is missing or any placeholder marker remains. Replace each one with a decision, or `N/A — reason`.

## Suitability & autonomy

| Question | Decision |
|----------|----------|
| Why an agent rather than a deterministic workflow or plain function? | TODO |
| Worst plausible action and its cost (money, data, people, reputation) | TODO |
| Autonomy level: `suggest` · `act-with-approval` · `act-and-audit` | TODO |
| Default behavior when uncertain or out of scope (ask / refuse / hand off) | TODO |

## Tool inventory

One row per tool the agent can call. Irreversible or external-facing tools need an approval gate or an explicit waiver here.

| Tool | Reversible? | Blast radius | Argument bounds (validated before execution) | Credential scope (whose identity) | HITL approval | Rate limit |
|------|-------------|--------------|-----------------------------------------------|-----------------------------------|---------------|------------|
| TODO | | | | | | |

## Trust boundaries

| Item | Decision |
|------|----------|
| Untrusted inputs (user, RAG, MCP/tool output, web, email, files, other agents) | TODO |
| Rule that tool/data content is data, never instructions — where enforced | TODO |
| Input screening (injection classifier, allowlists) | TODO |
| Output controls (PII/secret redaction, exfiltration channels blocked) | TODO |
| Least-privilege data access: source-system RBAC/ABAC propagated to the agent | TODO |
| Execution isolation for code/tool runs (sandbox, container, microVM) | TODO |

## Runtime limits

| Limit | Value | Enforcement on breach (warn / block / kill) |
|-------|-------|---------------------------------------------|
| Max steps per task | TODO | |
| Max tokens / cost per session | TODO | |
| Wall-clock timeout per task and per tool call | TODO | |
| Retry cap and circuit breaker per tool | TODO | |
| Fleet-wide spend ceiling | TODO | |

## Interruptibility

| Item | Decision |
|------|----------|
| How an operator stops one session / all sessions (kill-switch) | TODO |
| Graceful stop: state left behind, half-done actions compensated or rolled back | TODO |
| Fallback when the agent is disabled | TODO |

## Attribution & audit

| Item | Decision |
|------|----------|
| Unique agent instance id carried on every downstream call | TODO |
| On-behalf-of user identity propagated (no shared service account) | TODO |
| Human-readable action log: what was done, why, with which args (redacted) | TODO |
| Audit retention and who can read it | TODO |

## Monitoring

| Signal | Threshold / alert | Owner |
|--------|-------------------|-------|
| Guardrail interventions (blocks, redactions, escalations) as structured events | TODO | |
| Behavior drift / anomaly (tool mix, refusal rate, cost per task) | TODO | |
| Incident runbook for "agent did something wrong" | TODO | |

## Red-team & evals

| Item | Decision |
|------|----------|
| Adversarial suite (tool, cases path) — direct + indirect injection, tool hijack, prompt leak, loops | TODO |
| Trajectory evals (tool selection, routing, synthesis) and golden traces path | TODO |
| Pass thresholds that block `@qa` clearance | TODO |
| Code-spec tests named: denial path per gated tool, argument bounds, limit-trip stops run, kill works | TODO |
