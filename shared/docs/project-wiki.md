# ADLC5 Project Wiki

Team-shared, evidence-gated knowledge base for a **consumer repository**. Distinct from [knowledge-base/](knowledge-base/README.md) (craft books) and [feature working memory](../../core/guides/working-memory.md) (per-feature SDD addendum).

## Three knowledge layers

| Layer | Location | Purpose |
|-------|----------|---------|
| Framework KB | `docs/knowledge-base/` (adlc5) | PBE, CC, CA, HFDP, CLRS craft guidance |
| **Project wiki** | `wiki/` (consumer repo, **tracked**) | Compiled truths about *this codebase* |
| Feature memory | `.adlc5/{feature}/memory/` (**gitignored**) | Active feature addendum → promotes to wiki |

## Core rules

1. **Code over docs** — README and `docs/` are hints; claims need code evidence or `confidence: low`.
2. **No unverified writes to `entities/`** — agents draft; humans approve via promotion packet + `approved.json`.
3. **Whole-repo ingest** — monorepos: one entity per package/app root detected from workspace manifests.
4. **Promotion after Implement** — after `stage_status.implement: completed`, not before.
5. **Review delivery (Option C)** — `wiki/drafts/promote-{feature}/packet.md` plus AskQuestion batches in `@adlc5-project-wiki`.

## Directory layout

```text
wiki/
  SCHEMA.md
  index.md
  log.md
  entities/
  concepts/
  boundaries/
  drafts/
    ingest-{sha-short}/
    promote-{feature}/
  challenges/
sources/
  manifest.json
```

## Evidence block (required for promotion)

```markdown
- Claim text here.
  - evidence: `path/to/file.ext:start-end` @ `commit:abcdef1`
  - confidence: high | medium | low
  - last_verified: YYYY-MM-DD
```

**high** — path exists at HEAD and line range matches (validated by `wiki/validate-claim.sh`).  
**low** — doc-only or unverified; stays in `drafts/` or `challenges/` until validated.

## Workflows

### Ingest (brownfield)

Initialize the existing repository before ingesting team knowledge:

```bash
{adlc5_root}/scripts/init-workspace.sh --project . --with-project-wiki
{adlc5_root}/scripts/adlc5 repo-spec validate --workspace .
{adlc5_root}/scripts/adlc5 repo-index check --workspace .
```

Initialization creates missing `.agents/` constitution drafts and builds six
generated JSON artifacts in `.agent-cache/`: the manifest, repository index,
module map, symbols, dependency graph, and test map. These index eligible code
across the repository without storing source bodies; symbol/import extraction
varies by language and test matching is heuristic. Review the constitution drafts
before committing them; keep the cache gitignored. Refresh stale intelligence
with `adlc5 repo-index refresh --workspace .`. See
[repository context](../../core/guides/repository-context.md) for coverage and retrieval.

The project wiki is the human-reviewed knowledge layer on top of that generated
index. Ingest creates draft stubs, not an automatic explanation of the entire codebase:

```bash
{adlc5_root}/scripts/wiki/ingest-repo.sh --workspace . [--commit HEAD]
```

Produces `wiki/drafts/ingest-{sha}/` + updates `sources/manifest.json`. Human reviews before merging into `entities/`.

### During feature

Maintain `.adlc5/{feature}/memory/promotion-candidates.md` — claims discovered during Plan/Implement with evidence stubs.

### Promote (Implement complete)

```bash
{adlc5_root}/scripts/wiki/promote-prepare.sh --feature my-feature --workspace .
# Human: @adlc5-project-wiki promote-review (AskQuestion)
# Human: edit approved.json in wiki/drafts/promote-my-feature/
{adlc5_root}/scripts/wiki/promote-apply.sh --feature my-feature --workspace .
```

### Lint

```bash
{adlc5_root}/scripts/wiki/lint.sh --workspace .
```

## Agent retrieval (brownfield)

1. Read `wiki/index.md` for codebase-wide questions (modules, boundaries, conventions).
2. Read `.adlc5/{feature}/memory/INDEX.md` for the active feature only.
3. Load full files only when INDEX or wiki points there — see [working-memory.md](../../core/guides/working-memory.md).

Do not duplicate framework KB into wiki pages.

## Security

- Never store secrets, tokens, or PII in wiki pages.
- Redact paths that embed user emails before commit.

## See also

- [skills/project-wiki/SKILL.md](../../skills/project-wiki/SKILL.md) — orchestration
- [templates/wiki/SCHEMA.md](../../templates/wiki/SCHEMA.md) — maintainer contract
