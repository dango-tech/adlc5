# ADLC5 — Governing agent products

**When to use:** `state.product_type` is `agent` — the feature ships an AI agent that calls tools, reads internal data, or takes actions for users. This governs the **L3 agent product**, not the coding agent building it (see [agent-orchestration.md](agent-orchestration.md)).

**Artifact:** `design/1d-agent-governance.md` from [templates/agent-product/agent-governance.md](../../templates/agent-product/agent-governance.md). `plan-complete` check `agent_governance` fails until every section is present and no `TODO` remains.

**Sources:** OpenAI, *Practices for Governing Agentic AI Systems* (Shavit et al., 2023) — https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf · OWASP Top 10 for LLM Applications — https://genai.owasp.org/ · MITRE ATLAS — https://atlas.mitre.org/. Recheck these per [current-information.md](current-information.md) before quoting versions.

---

## Failure vectors to design against

| Vector | What goes wrong | Core controls |
|--------|-----------------|---------------|
| **Data leakage / over-provisioned access** | Agent runs on a broad service credential, or pulls context via RAG/MCP, and exposes PII, financials, or source to the wrong user | Propagate source-system RBAC/ABAC; scope tool parameters; redact PII on input and output |
| **Runaway actions / loops / cost spikes** | Retry loops, API spam, budget exhaustion, cascading outages | Per-session token/cost ceilings, step limits, circuit breakers, timeouts — wired to a real block |
| **Unauthorized or irreversible operations** | Refunds, row deletes, prod config changes, external messages with no accountability | Tool allowlist, pre-execution argument validation, HITL approval for destructive/high-risk tools |
| **Prompt injection / jailbreak / tool hijacking** | User input or poisoned data makes the agent ignore instructions, leak prompts, or misuse tools | Input screening, data-vs-instruction trust boundary, sandboxed execution |

## Governance practices → ADLC5 step

| # | Practice | Where ADLC5 enforces it | Governance section |
|---|----------|-------------------------|--------------------|
| 1 | Evaluate suitability for the task | `@discover` framing; Specify NFR **Autonomy & agency** | Suitability & autonomy |
| 2 | Constrain the action space; require approval | Plan threat model (agentic threats) | Tool inventory |
| 3 | Set safe default behaviors | Specify NFR | Suitability & autonomy |
| 4 | Make agent activity legible | Plan ops design | Attribution & audit |
| 5 | Automatic monitoring | Plan ops design; `deploy` runbook | Monitoring |
| 6 | Attributability | Plan contracts/ops | Attribution & audit |
| 7 | Interruptibility and control | Plan ops; Tasks code spec tests | Interruptibility, Runtime limits |

## Stage instructions

**Discover / Specify**
- Ask first whether an agent is the right tool; a deterministic workflow is often safer and cheaper.
- Set `product_type`: `./scripts/adlc5 state set --feature {feature} --patch '{"product_type":"agent"}'`.
- Record the **Autonomy & agency** NFR row in `spec-handoff.md` ([03-nfr.md](../../skills/specify/phases/03-nfr.md)).

**Plan** (`plan-6-design-operations`)
- Add the agentic threats to the STRIDE pass ([01-engineering-design.md](../../skills/plan/phases/01-engineering-design.md)).
- Fill `design/1d-agent-governance.md`. Every irreversible or external-facing tool either has an HITL gate or a written waiver.
- Limits are enforced in code, not prompts: a model cannot be trusted to obey its own budget.

**Tasks** (`tasks-2-code-spec`)
- Each governance control becomes a test before code: denial path per gated tool, argument bounds, injection fixture (poisoned tool output), limit trip stops the run, kill-switch works.

**Implement / QA** (`implement-4-qa`)
- Run the agent red-team in [`@qa` Phase 1](../../skills/qa/phases/01-security-scanning.md#agent-red-team-product_type-agent). Critical injection or unauthorized-action findings block clearance like SQL injection does.

**Deploy**
- Before go-live: guardrail events reach structured logs with an owner, drift alert exists, kill-switch tested in the target environment.

## Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| Safety rules only in the system prompt | Injection rewrites them; enforce at the tool boundary |
| One service account for every user | Agent can read what the user cannot — leakage by design |
| Budget is a spec cell with no enforcement | Nothing stops the loop until the invoice arrives |
| Evals score only the final answer | Unsafe tool calls along the way go unseen |
| Tool output fed back as trusted instructions | Indirect injection via RAG, email, web pages |
