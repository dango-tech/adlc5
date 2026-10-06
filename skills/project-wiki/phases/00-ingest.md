---
name: project-wiki-ingest
description: Brownfield ingest — whole repo draft at pinned commit.
---

# Ingest

## Steps

1. Confirm `project_wiki.enabled` in `.adlc5/config.yaml`.
2. If `wiki/` missing: `{adlc5_root}/scripts/wiki/init-wiki.sh --workspace .`
3. Run `{adlc5_root}/scripts/wiki/ingest-repo.sh --workspace .`
4. Summarize draft path `wiki/drafts/ingest-{sha}/` for human review.
5. Remind: **do not** merge into `entities/` without validation.

## Agent follow-up

- For each high-value stub, deepen using code (not README alone).
- Run `validate-claim.sh` before suggesting `confidence: high`.
- Stale docs → `wiki/challenges/doc-vs-code-{topic}.md`.
