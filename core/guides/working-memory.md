# ADLC5 — Working memory (token-efficient feature context)

**Canonical store:** workspace-only — `.adlc5/{feature}/memory/` (not Obsidian, not chat history).

Use this guide in every `@adlc5*` stage skill and implementation subagent.

---

## Three layers

| Layer | Path | When to load |
|-------|------|--------------|
| **L0 State** | `.adlc5/{feature}/state.json` | Every invocation — canonical schema-v3 JSON only |
| **L1 Index + packs** | `.adlc5/{feature}/memory/INDEX.md`, `summaries/`, `context-packs/` | Every invocation — read INDEX first |
| **L2 Artifacts** | `design/`, `tasks/stories.md`, `tasks/code-spec/`, etc. | Only when INDEX/pack points there or user requests depth |

**Cold knowledge** (books, lifecycle): [../knowledge-base/](../../shared/docs/knowledge-base/README.md) and [../playbook.md](../../shared/docs/playbook.md) — not feature working memory.

**OKF pattern catalog** (`shared/docs/patterns/`): **pull-on-demand**, never L1 always-on. Lookup ids via `./scripts/adlc5 patterns lookup`; open ≤3 cards only when Spec/Plan/S3/S5 need them. Do not copy catalog into `memory/` or context packs unless a story names a pattern.

---

## Directory layout

```text
.adlc5/{feature}/
  state.json
  design/
  tasks/code-spec/
  memory/
    INDEX.md
    summaries/
      specify.md
      plan.md
      tasks.md
      implement.md
    context-packs/
      story-{id}.md
      verify-{id}.md
```

Templates: [templates/memory/](../../templates/memory)

---

## INDEX.md contract

On every invocation after L0 state:

1. Read `memory/INDEX.md` if it exists.
2. Load **only** artifact paths listed for the active stage/phase/story.
3. **Do not** paste full code specs or multi-file design corpora into orchestrator chat.

INDEX must include:

- Feature name, `current_stage`, `current_step`, `last_compacted`, `updated_at`
- Table: `artifact_path | phase | summary (≤120 chars)`

Example row:

```text
| .adlc5/my-feature/tasks/code-spec/US-001.md | tasks-2-code-spec | Login API — JWT, 3 endpoints, 12 tests | |
```

---

## State schema extensions

**Lifecycle** (`.adlc5/{feature}/state.json`):

```json
"memory": {
  "index_path": ".adlc5/{feature}/memory/INDEX.md",
  "last_compacted": "spec",
  "context_pack_policy": "subagent_minimal"
}
```

**Implementation policy** (canonical `state.json` plus feature `policies.yaml`):

```json
"memory": {
  "story_packs": {
    "US-001": ".adlc5/{feature}/memory/context-packs/story-US-001.md"
  }
},
"retry_policy": {
  "max_implementation_attempts": 3,
  "max_rework_attempts": 3,
  "transient_retry": true,
  "escalate_on_spec_signal": true
},
"context": {
  "verify_policy": "hitl",
  "integrate_policy": "hitl"
}
```

`retry_policy` is **additive** — omit for legacy state; orchestrator uses defaults. Classifier: `./scripts/delivery-retry-classifier.py`. Policies: [policies.yaml.example](../../templates/policies.yaml.example).

---

## Initialization (first `@adlc5` invoke)

When creating `.adlc5/{feature}/` for a new feature:

1. Create `memory/`, `memory/summaries/`, `memory/context-packs/`.
2. Copy structure from [templates/memory/INDEX.md](../../templates/memory/INDEX.md) into `memory/INDEX.md` (fill feature name, timestamps).
3. Copy [templates/memory/promotion-candidates.md](../../templates/memory/promotion-candidates.md) to `memory/promotion-candidates.md` when project wiki is enabled.
4. Set `memory.index_path` and `memory.last_compacted: null` in lifecycle `state.json`.

---

## Compaction protocol (mandatory at phase gates)

To automate the compaction and INDEX regeneration protocol, call the compaction script:

```bash
./scripts/compact-memory.py --feature "{feature-name}"
```

This script automatically scans `.adlc5/{feature}/` for design documents, user stories, code specs, and context packs, generates a clean, compliant `memory/INDEX.md` index file, and updates the memory metadata block in the state JSON.

At the end of each **ADLC5 stage** and significant canonical step:

1. Write or update `memory/summaries/<name>.md` (≤2–3 pages: decisions, constraints, open questions, links — **no full artifact duplication**).
2. Refresh `memory/INDEX.md` with all artifact paths and one-line summaries.
3. Update `memory.last_compacted` in canonical `.adlc5/{feature}/state.json`.
4. **`tasks-2-code-spec` complete:** generate `context-packs/story-{id}.md` per story and register paths in `memory/INDEX.md`.

| Event | Summary file |
|-------|----------------|
| Specify completed | `summaries/specify.md` |
| Plan completed | `summaries/plan.md` |
| Tasks completed | `summaries/tasks.md` + all `context-packs/story-*.md` |
| Implement build/verify | `summaries/implement.md` |
| Implement completed | `summaries/implement.md` + verification/QA/PR evidence paths |

---

## Subagent context policy

| Subagent | Read order |
|----------|------------|
| `@build-implementer` | `context-packs/story-{id}.md` → code spec file → coding guides. Never sibling story specs. |
| `@assure-verifier` | `context-packs/verify-{id}.md` → code spec file. Never full design corpus. |
| Discover / PRT handoff | `summaries/spec.md` or upstream summary paths — not full council dumps in orchestrator chat |

Orchestrator spawning subagents: pass **pack path + story id**, not full spec body in the Task prompt.

---

## Retrieval rules (mandatory)

- **Orchestrators:** INDEX + active phase summary only; cite artifact paths instead of inlining.
- **Subagents:** Context pack first; one code spec max per invocation.
- **Resume:** Read INDEX → identify `last_compacted` → load matching summary + paths for current work only.
- **Rework:** Update summary + INDEX when artifacts change; bump `last_compacted` label.

---

## What never belongs in chat

- Full per-story code specs when a context pack exists
- Entire `tasks/stories.md` when `summaries/tasks.md` exists
- All three design documents when only 1c ops context is needed
- Full knowledge-base files (use KB paths by reference)
- OKF pattern catalog indexes or card bodies (pull-on-demand via lookup; cite ids)

---

## Execution personas

When `policies.yaml` → `persona_mode.enabled: true`, summaries and packs are **persona-owned**, not only stage-owned.

| Persona | Owns summaries / packs | Deny (feature artifacts) |
|---------|--------------------------|---------------------------|
| Analyst | `summaries/specify.md`, PRT/discover artifacts | `design/`, `tasks/code-spec/` |
| Architect | `summaries/plan.md`, `design/`, `tasks/code-spec/` | `verify/`, product `src/` (during Plan) |
| Coder | `context-packs/story-*.md`, code specs | full design corpus in pack |
| Tester | `context-packs/verify-*.md`, verify/QA artifacts | write access to product code |

Validation:

```bash
./scripts/memory/persona-pack-filter.sh --feature F --persona analyst --paths PATH ...
./scripts/memory/budget-check.py --feature F --persona coder --paths PATH ...
```

Gate: `persona_context_violation` in `check-gates.py` when forbidden paths are loaded.

Registry: [core/personas.yaml](../../core/personas.yaml)

---

## Project wiki (team-shared, optional)

**Not** feature memory — compiled repo truths in tracked `wiki/`. Feature addendum promotes **after Implement completes**.

| Concern | Location |
|---------|----------|
| Spec | [docs/project-wiki.md](../../shared/docs/project-wiki.md) |
| Promotion candidates | `.adlc5/{feature}/memory/promotion-candidates.md` |
| Human review packet | `wiki/drafts/promote-{feature}/` |
| Invoke | `@adlc5-project-wiki` |

During a feature: append validated candidates to `promotion-candidates.md`. Do not write `wiki/entities/` directly.

---

## Consumer repo note

`.adlc5/` is typically **gitignored** in application repos. Working memory travels with the feature workspace, not the adlc5 distribution repo. **`wiki/` is tracked** when project wiki is enabled.
