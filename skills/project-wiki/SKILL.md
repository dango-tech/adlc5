---
name: adlc5-project-wiki
description: ADLC5 Project Wiki — team-shared repo KB with evidence-gated ingest, lint, and Implement-complete promotion from feature memory. Optional brownfield bootstrap during Plan.
---

# ADLC5 Project Wiki

**Invoke:** `@adlc5-project-wiki` with subcommand: `init` | `ingest` | `lint` | `promote-prepare` | `promote-review` | `promote-apply` | `query`

**Spec:** [docs/project-wiki.md](../../shared/docs/project-wiki.md)

**Scripts (mandatory):** `{adlc5_root}/scripts/wiki/*.sh` — do not reimplement logic inline.

Resolve `adlc5_root` from `.adlc5/workspace.json` or `.adlc5/config.yaml` in the consumer project.

---

## Prerequisites

Consumer `.adlc5/config.yaml`:

```yaml
project_wiki:
  enabled: true
  root: wiki
```

If `enabled: false`, stop and tell the user to enable or run `init-workspace.sh --with-project-wiki`.

---

## Subcommands

| Subcommand | Script | When |
|------------|--------|------|
| `init` | `init-wiki.sh` | First-time wiki scaffold |
| `ingest` | `ingest-repo.sh` | Brownfield (Plan optional) |
| `lint` | `lint.sh` | Health check |
| `promote-prepare` | `promote-prepare.sh` | **After Implement completes** |
| `promote-review` | *(this skill)* | AskQuestion from `review-questions.json` |
| `promote-apply` | `promote-apply.sh` | After human writes `approved.json` |
| `query` | read `wiki/index.md` | Cross-feature / brownfield questions |

---

## promote-review (Option C)

**Hard gate:** `stage_status.implement: completed` in `.adlc5/{feature}/state.json`.

1. Run `promote-prepare.sh` if `wiki/drafts/promote-{feature}/review-questions.json` is missing.
2. Read `review-questions.json` — batch up to **2 questions per AskQuestion** call.
3. Each question must show **claim + evidence paths** in the prompt text (help human validate quickly).
4. Map answers to `wiki/drafts/promote-{feature}/approved.json`:

```json
{
  "feature": "{feature}",
  "approved_at": "{ISO}",
  "approved_by": "user",
  "candidates": [
    { "id": "...", "action": "promote_entity", "target": "wiki/entities/slug.md" }
  ]
}
```

Use option ids: `promote_entity`, `promote_concept`, `reject`, `investigate`.

5. Tell user to run `promote-apply` or invoke `@adlc5-project-wiki promote-apply` after saving `approved.json`.

**Never** write directly to `wiki/entities/` without `approved.json` + `promote-apply.sh`.

---

## During feature work

- Maintain `.adlc5/{feature}/memory/promotion-candidates.md` (template: [templates/memory/promotion-candidates.md](../../templates/memory/promotion-candidates.md)).
- Validate evidence: `validate-claim.sh --evidence "path:line-line"`.
- User assertions → draft only until validated; contradictions → `wiki/challenges/`.

---

## Retrieval (all ADLC5 agents)

Brownfield or cross-cutting questions:

1. `wiki/index.md`
2. Linked entity/concept pages
3. Feature `memory/INDEX.md` if scoped to active feature

---

## Parent hooks

- **@adlc5-plan** — [phases/00-ingest.md](phases/00-ingest.md) when Plan needs project context
- **@adlc5-implement** — [phases/09-wiki-promote.md](phases/01-promote-review.md) after `stage_status.implement: completed`
