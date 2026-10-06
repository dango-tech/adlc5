# ADLC5 Playbook

Operational reference for **spec → excellent code** with TDD and craftsmanship skills.

**Lifecycle:** Specify → Plan → Tasks → Implement → `pr-ready` — [docs/ADLC5.md](../../docs/ADLC5.md)

**Install:** [INSTALL.md](INSTALL.md) · **Invokes:** [SKILL-MAP.md](SKILL-MAP.md) · **Agent map:** [AGENTS.md](../../AGENTS.md)

**Mantra:** Repeatable work → scripts; skills orchestrate scripts against the SDD (Software Design Document).

---

## Stages and gates

| Stage | Skill | Exit gate |
|-------|-------|-----------|
| Specify | `@adlc5-specify` | `specify-complete` |
| Plan | `@adlc5-plan` | `plan-complete` |
| Tasks | `@adlc5-tasks` | `tasks-complete` |
| Implement | `@adlc5-implement` | `pr-ready` |

```bash
./scripts/check-gates.py --feature NAME --gate pr-ready
```

Gate registry: [core/gates.yaml](../../core/gates.yaml)

**Entry:** `@adlc5 for [feature]` · State: `.adlc5/{feature}/state.json`

Optional upstream: `@discover` → `@prt` during Specify.

**Current-information rule:** versions, APIs, protocol maturity, provider
capabilities, security guidance, and current recommendations must be revalidated
against official primary sources during Specify/Plan. Tracked snapshots record
`last_verified`, status, and source URLs; stale information is a blocker. See
[current-information.md](../../core/guides/current-information.md).

---

## Craftsmanship skills (when to invoke)

OKF catalog is **pull-on-demand** (≤3 cards): `./scripts/adlc5 patterns lookup --tags …` — never dump indexes into every turn. Cite concept ids in design docs.

| When | Invoke | OKF catalog (load first) | Knowledge base (deep) |
|------|--------|--------------------------|------------------------|
| Layer boundaries, dependency rule | `@clean-architecture-review` (S2) | [patterns/architecture/](patterns/architecture/index.md) | [03-clean-architecture.md](knowledge-base/03-clean-architecture.md) |
| GoF / structural design | `@design-pattern-advisor` (S3) | [patterns/gof/](patterns/gof/index.md) | [04-design-patterns.md](knowledge-base/04-design-patterns.md) |
| Scale NFRs, hot-path O(·) | `@algorithm-advisor` (S3b) | [patterns/algorithms/](patterns/algorithms/index.md) | [05-algorithms-clrs.md](knowledge-base/05-algorithms-clrs.md) |
| Pattern selection from reqs | `@pbe-select-patterns` (S5) | [patterns/index.md](patterns/index.md) | [01-pbe.md](knowledge-base/01-pbe.md) |
| TDD implementation | `@adlc5-tdd`, `@build-implementer` | cite ids only if story names a pattern | [02-clean-code.md](knowledge-base/02-clean-code.md) |
| PR / diff review | `@craftsmanship-code-review` (S1), `@pbe-review-with-patterns` (S6) | cite concept ids | KB Part II, Part I |
| Hot-path review | `@complexity-review` (S3c) | [algorithms/anti-patterns](patterns/algorithms/anti-patterns.md) | [05-algorithms-clrs.md](knowledge-base/05-algorithms-clrs.md) |
| Security & quality gate | `@qa` | — | project policies |
| Open / review PR | `@pr-reviewer` | — | [skills/pr-reviewer/](../../skills/pr-reviewer) |

Rules R0–R5 (`.cursor/rules/` or [shared/rules/portable/](../rules/portable/)) apply on every edit.

Full skill index: [SKILL-MAP.md](SKILL-MAP.md)

---

## Knowledge base

Primary reference for agents — cite these, not external PDFs.

| File | Use for |
|------|---------|
| [00-executive-summary.md](knowledge-base/00-executive-summary.md) | How pillars combine |
| [01-pbe.md](knowledge-base/01-pbe.md) | Patterns as assets, consumption |
| [02-clean-code.md](knowledge-base/02-clean-code.md) | Names, functions, tests, smells (G/F/N/T) |
| [03-clean-architecture.md](knowledge-base/03-clean-architecture.md) | Layers, boundaries, dependency rule |
| [04-design-patterns.md](knowledge-base/04-design-patterns.md) | GoF selection, OO principles |
| [05-algorithms-clrs.md](knowledge-base/05-algorithms-clrs.md) | O(·), data structures, decision tables |
| [06-synthesis.md](knowledge-base/06-synthesis.md) | Cross-book decision flow |

Index: [knowledge-base/README.md](knowledge-base/README.md)

OKF craftsmanship catalog (tool entrypoint): [patterns/index.md](patterns/index.md) · governance: [patterns/README.md](patterns/README.md) · lookup: `./scripts/adlc5 patterns lookup --tags …`

---

## Brownfield and large repos

Default mode is **brownfield** — extend existing paths; do not invent folder trees (`init-feature.sh --mode brownfield`).

On any codebase, load the compact repository constitution before feature SDD. On a
large or unfamiliar codebase, use generated repository intelligence for navigation
and the optional project wiki for deeper approved knowledge.

| Layer | Location | Role |
|-------|----------|------|
| Framework KB | adlc5 `shared/docs/knowledge-base/` | *How* to write excellent code (books) |
| **Repository constitution** | consumer `.agents/` (**tracked**) | Current architecture, boundaries, commands |
| Repository intelligence | consumer `.agent-cache/` (**gitignored**) | Generated symbols, modules, dependencies, tests |
| **Project wiki** | consumer `wiki/` (**tracked**) | *What this codebase is* (evidence-backed) |
| Feature memory | `.adlc5/{feature}/memory/` (**gitignored**) | Active feature scope; promotes to wiki after delivery |

**Automatic (default):** `init-feature.sh --mode auto` runs `scripts/profile-repo.py` and `scripts/wiki/ensure-wiki.sh`:

| Profile | Size (code files) | Wiki action |
|---------|-------------------|-------------|
| greenfield | any | skip |
| brownfield | < 150 (small) | skip |
| brownfield | 150–1499 (medium) | init wiki; ingest if empty/stale |
| brownfield | ≥ 1500 (large) | init + ingest if empty/stale |

Override in `.adlc5/config.yaml`: `project_wiki.enabled: false` or `ingest_on: large` (raise threshold).

Manual profile: `./scripts/profile-repo.py --workspace .`

Full spec: [project-wiki.md](project-wiki.md)

---

## Greenfield repos

| Profile | Action |
|---------|--------|
| Greenfield | Story 0 runs official scaffold from [scaffold-registry.md](../../core/guides/scaffold-registry.md) |
| Brownfield | Use existing paths |
| Waived | User chooses via AskQuestion → `layout_compliance: waived` |

---

## Working memory and models

| Topic | Guide |
|-------|-------|
| Feature memory (INDEX, packs) | [working-memory.md](../../core/guides/working-memory.md) |
| Model tiers per stage | [model-matrix.md](../../core/guides/model-matrix.md) |
| Clarity gate (Spec/Plan) | [clarity-scoring.md](../../core/guides/clarity-scoring.md) |
| Structured user choices | [askquestion-convention.md](../../core/guides/askquestion-convention.md) |

Compaction: `scripts/memory/compact-stage.sh` at stage exits.

---

## Production-ready

After `init-workspace.sh`, governance copies to `.adlc5/governance/`. Per feature: copy `definition-of-done.md` into `.adlc5/{feature}/`.

`verified` on a story ≠ production-ready — exit on `check-gates.py --gate pr-ready`.

---

## Optional: project wiki

Team KB in tracked `wiki/` — [project-wiki.md](project-wiki.md) · `@adlc5-project-wiki` · init: `init-workspace.sh --with-project-wiki`

---

## AI agent products

Building an agent system (not just agent-assisted delivery): [07-ai-agent-orchestration.md](knowledge-base/07-ai-agent-orchestration.md) · [agent-orchestration.md](../../core/guides/agent-orchestration.md)
