# AI Agent Orchestration — Conceptual Guide

**Purpose:** Cloud- and vendor-neutral concepts for designing, building, evaluating, and operating **AI agent systems**. Use when the product or feature *is* an agent (or multi-agent workflow), not only when the delivery tool is an AI coding assistant.

**Inspiration:** Skill-suite + CLI patterns from coding-agent tooling (e.g. [google/agents-cli](https://github.com/google/agents-cli)) — distilled here without binding to Google Cloud, AWS, or any single agent framework.

**ADLC5 mapping:** [core/guides/agent-orchestration.md](../../../core/guides/agent-orchestration.md)

---

## 1. Four layers (keep them separate)

| Layer | Role | Examples (illustrative only) |
|-------|------|------------------------------|
| **L1 — Host coding agent** | Helps humans write and change software | IDE agents, CLI assistants |
| **L2 — Delivery orchestration** | Runs *your* SDD lifecycle: spec → build → assure | ADLC5, internal playbook skills |
| **L3 — Agent runtime / framework** | Executes agent logic: tools, state, graphs | Any framework or custom loop |
| **L4 — Execution substrate** | Where the agent process runs | Container, VM, serverless, local — **pluggable detail** |

**Rule:** L2 skills must not be confused with L3. The coding agent that implements your repo is not the same as the agent product you ship to end users.

```text
Human → L1 (coding agent) → L2 (delivery orchestration) → codebase
                                              ↓
End user → L3 (agent product) → L4 (runtime)
```

---

## 2. Skill-suite pattern (lifecycle capabilities)

Mature agent platforms expose **composable skills** (or playbooks) aligned to lifecycle phases — not one mega-prompt.

| Conceptual skill | Teaches the coding agent | Vendor-neutral outcome |
|----------------|--------------------------|-------------------------|
| **Workflow** | End-to-end lifecycle, when to stop, model/tier choice, code preservation | Repeatable delivery path |
| **Scaffold** | Create, enhance, upgrade project shape | Official layout, no hand-rolled trees |
| **Runtime code** | Framework APIs: agents, tools, memory, callbacks, subgraphs | Correct use of L3 primitives |
| **Evaluation** | Metrics, datasets, judges, regression gates | Evidence before release |
| **Release** | Package, attach runtime, register in a catalog | Reproducible deploy artifact |
| **Observability** | Traces, logs, cost/latency, failure taxonomy | Operable in production |

**ADLC5 mantra alignment:** Repeatable steps → **scripts**; judgment and routing → **skills** reading SDD/state.

---

## 3. CLI + skills (dual interface)

| Mode | Who drives | When |
|------|------------|------|
| **Human CLI** | Engineer in terminal | CI, one-off ops, deterministic flags |
| **Agent-driven** | Host coding agent invokes CLI via skills | Greenfield scaffold, deploy, eval from chat |

Both should call the **same** underlying commands so behavior does not drift.

---

## 4. Agent product lifecycle (conceptual)

| Phase | Goal | Typical artifacts |
|-------|------|-------------------|
| **Frame** | Problem, users, boundaries, policies | Brief, constraints, HITL points |
| **Scaffold** | Canonical project skeleton | Manifest, layout doc, Story 0 |
| **Implement** | Tools, prompts, orchestration graph | Source, contracts, tests |
| **Evaluate** | Quality before release | Eval sets, baselines, thresholds |
| **Release** | Attach to runtime, version, secrets | Build artifact, config, rollout plan |
| **Observe** | Run health, drift, incidents | Dashboards, SLOs, runbooks |
| **Govern** | Access, data, audit, kill-switch | Policy docs, STOP files, budgets |

Brownfield: **enhance** existing repos (add eval, release, observability) instead of only **create**.

---

## 5. Orchestration patterns (inside L3)

Pick explicitly in design — do not default to “one big LLM call.”

| Pattern | Structure | Use when |
|---------|-----------|----------|
| **Single agent** | One loop, tools, memory | Narrow task, low coordination cost |
| **Supervisor + workers** | Planner delegates bounded subtasks | Parallel stories, specialized roles |
| **Pipeline** | Fixed stages, handoff artifacts | ETL-style flows, compliance steps |
| **Council / ensemble** | Same brief, independent models, synthesis | Exploration, risk challenge |
| **Human-in-the-loop** | Gates before irreversible actions | Policy, safety, low clarity |
| **Evaluator loop** | Implement → verify → rework | Quality bars, spec compliance |

**Concepts:** Supervisor owns **state**; workers are **stateless** relative to lifecycle; pass **minimal context** (packs, not full corpora).

---

## 6. Evaluation (vendor-neutral)

| Concept | Meaning |
|---------|---------|
| **Eval set** | Fixed inputs + expected properties (not always single “golden” string) |
| **Trajectory** | Tool calls and intermediate steps, not final text only |
| **Judge** | Model or rule that scores output against rubric |
| **Baseline** | Stored run to detect regression |
| **Gate** | CI or Implement-stage block if metric below threshold |

Evaluation belongs in **Plan** (tests/metrics named before code) and **Implement** (run before release).

---

## 7. Release and runtime (abstract)

Avoid naming a cloud; think in capabilities:

| Capability | Question to answer |
|------------|-------------------|
| **Artifact** | What is immutable per version? (image, wheel, bundle) |
| **Runtime attachment** | How does the process start, scale, and stop? |
| **Registration** | How do clients discover version and endpoint? |
| **Secrets** | Where do keys live; never in repo or wiki |
| **Rollback** | Previous artifact still runnable? |

Stack-specific CLIs (when used) are **adapters** in [scaffold-registry.md](../../../core/guides/scaffold-registry.md) — not part of this conceptual layer.

---

## 8. Observability (abstract)

| Signal | Why |
|--------|-----|
| **Trace / span** | Follow one user request across tools and sub-agents |
| **Structured log** | Query failures; include correlation id |
| **Cost & latency** | Budget per session; autopilot kill-switch |
| **Tool audit** | What was called, with what args (redacted) |

### Token/cost collection pattern (vendor-neutral)

A budget row in a spec is not a mechanism. Apply the same shape ADLC5 uses on **its own** delivery work — [`scripts/memory/usage-ledger.py`](../../../scripts/memory/usage-ledger.py), `adlc5 usage record` / `usage summary` / `usage fleet`, mapped in [agent-orchestration.md](../../../core/guides/agent-orchestration.md) — to the agent product's **own** LLM calls, not only to the coding-agent building it:

1. **Per-call record.** One structured event per model call: model id, tier, token counts by type (input/output/cache/thinking — whatever the provider exposes), session/thread/request id, tool or step name, timestamp. Append-only; a call that fails to record is a bug in the wrapper, not a reason to block the call.
2. **Session rollup.** Aggregate per session/thread/request as it runs — this is what a per-session budget check reads, and what feeds the kill-switch/STOP-file pattern in §4's **Govern** phase.
3. **Fleet rollup.** Aggregate across sessions/users/deployments for fleet-wide cost visibility — the same aggregation at wider scope, not a second system.
4. **Budget enforcement.** A threshold check against the session rollup wired to a real control — warn, block the next call, or trip the kill-switch — not a dashboard nobody reads until the invoice arrives.

Keep counters generic (per-field, not one opaque "cost" number) — providers expose different counters, and pricing changes; a raw token ledger outlives any specific price you compute from it today.

---

## 9. Model and tier selection (conceptual)

| Tier | Cognitive load | Typical assignment |
|------|----------------|-------------------|
| **Reasoning** | Multi-doc synthesis, security, verification, council | Design, code spec, eval design |
| **Balanced** | Orchestration, stories, integration | Parent agents, stage runners |
| **Implementation** | Bounded TDD in listed files | Worker subagents — inherit parent, avoid “fast” tier |
| **Fast** | Routing only | Not for implement, verify, or security |

Same tier ideas as [model-matrix.md](../../../core/guides/model-matrix.md) — host maps tiers to concrete model IDs in config.

Tier routing is the design lever for cost; §8's per-call ledger is how you verify it's actually working in production — whether `fast`-tier calls are cheaper in practice, and whether `reasoning` tier is over-assigned relative to the cognitive load it's spent on.

---

## 10. Anti-patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| Coding agent invents project tree on greenfield | Drift from official scaffold; verifier cannot trust layout |
| One prompt owns spec + code + deploy | No gates, no eval, no audit trail |
| Workers write lifecycle state | Race conditions, unclear source of truth |
| Full spec pasted into every subagent | Context blow-up, cross-story leakage |
| Release without eval baseline | Silent quality regression |
| Cloud console knowledge baked into core spec | Locks architecture to one vendor |
| Cost/latency budget is a spec cell, no per-call ledger | Budget is a guess; the kill-switch has nothing to check against |

---

## 11. Composability

Agent lifecycle skills are **one suite** among several:

- **Delivery** (ADLC5) — ship the agent product as software
- **Craft** (PBE, CA, CC) — structure and quality of code
- **Repo memory** (project wiki) — brownfield truths about the codebase
- **Domain skills** — security, data, frontend, etc.

Install only what the feature needs; document which suite owns which phase in the SDD.

---

## Related

- [06-synthesis.md](06-synthesis.md) — five-layer craftsmanship stack
- [../playbook.md](../playbook.md) — ADLC5 stages and craftsmanship
- External reference (stack-specific tooling example): [google/agents-cli](https://github.com/google/agents-cli)
