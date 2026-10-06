# Project Wiki — Maintainer Schema

Agents maintain this wiki; humans approve promotions into `entities/`, `concepts/`, and `boundaries/`.

## Write permissions

| Path | Agent | Human |
|------|-------|-------|
| `drafts/`, `challenges/` | create/update | review |
| `entities/`, `concepts/`, `boundaries/` | **never direct** | via `promote-apply` only |
| `index.md` | via `rebuild-index.sh` or promote-apply | — |
| `log.md` | append on ingest/promote/lint | — |

## Evidence (required for `confidence: high`)

```yaml
evidence: "relative/path/file.ts:10-40"
commit: "abcdef1"   # optional; default HEAD at verify time
confidence: high | medium | low
last_verified: YYYY-MM-DD
```

Run validation before claiming **high**:

```bash
{adlc5_root}/scripts/wiki/validate-claim.sh --workspace . --evidence "path:10-40"
```

## Ingest

1. Run `ingest-repo.sh` at a pinned commit.
2. Draft under `drafts/ingest-{sha}/` — do not edit `entities/` inline.
3. Log append: `## [ISO] ingest | {sha-short}`

Code-first: workspace roots from `package.json`, `pnpm-workspace.yaml`, `go.work`, `Cargo.toml`, etc. Doc claims without code proof → `challenges/doc-vs-code-*.md`.

## Query

1. Read `index.md`.
2. Open linked pages; cite paths in answers.
3. Optional: file synthesis to `concepts/` as draft only.

## Lint

Run `lint.sh` before PRs touching wiki. Fix contradictions in `challenges/` before raising confidence.

## Promotion (after Implement completes)

1. Source: `.adlc5/{feature}/memory/promotion-candidates.md` and summaries.
2. `promote-prepare.sh` → `drafts/promote-{feature}/packet.md` + `review-questions.json`.
3. `@adlc5-project-wiki promote-review` — AskQuestion per batch (Option C).
4. Human writes `approved.json` (ids only).
5. `promote-apply.sh` merges into wiki; append `log.md`.

## Feature memory link

Feature `memory/INDEX.md` may reference `wiki/entities/*.md` for boundaries already promoted. Do not copy full entity bodies into feature memory.

## Conflicts

If feature claim contradicts wiki entity: create `challenges/` entry with both evidences; human resolves in promotion review.
