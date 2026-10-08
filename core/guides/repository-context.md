# Repository context

**Intelligence is ADLC5's fifth pillar.** It connects Specify, Plan, Tasks, and
Implement through repository knowledge, reviewed guidance, focused context packs,
and evidence-based progression. Models supply reasoning; ADLC5 supplies context
and deterministic checks. SOUL is the supporting reasoning discipline.

ADLC5 keeps repository-wide context separate from feature SDD.

| Layer | Location | Ownership | Loading rule |
|-------|----------|-----------|--------------|
| Repository constitution | `AGENTS.md`, `.agents/`, `docs/adr/` | Human-reviewed, tracked | Read first |
| Repository intelligence | `.agent-cache/` | Generated, gitignored | Query after constitution |
| Project wiki | `wiki/` | Human-approved, tracked, optional | Load linked detail on demand |
| Feature SDD | `.adlc5/{feature}/` | Feature-local working state | Load active feature only |

## Canonical `.agents/` layout

Constitution lives under the same project folder as skill links — **`.agents/`**, never `.agent/`.

```text
.agents/
  architecture.yaml
  boundaries.yaml
  commands.yaml
  schemas/task-spec.schema.json
  skills/                    # project-local ADLC5 skill symlinks
  <any pre-existing files>   # leave in place
```

`.adlc5/governance/` is a different layer (DoD / production-ready copies). Do not move those files into `.agents/`.

## Repository constitution

`repo-spec init` creates missing files but never overwrites them. If a legacy `.agent/` constitution exists, init **copies** missing files into `.agents/` and leaves the legacy copies for you to delete after review.

```bash
./scripts/adlc5 repo-spec init --workspace .
./scripts/adlc5 repo-spec reconcile --workspace .
./scripts/adlc5 repo-spec validate --workspace .
```

Generated starting content has `status: draft`. Humans promote it by editing and
reviewing it in Git. A feature that changes architecture, boundaries, or canonical
commands proposes the matching constitution change in the same PR.

For a brownfield repository, run initialization once, inspect every generated or
adopted file, replace `unknown` values with the actual architecture and boundaries,
then commit the reviewed `.agents/` constitution. For a greenfield repository,
initialize before the first feature, fill in the intended boundaries and commands,
and update the tracked constitution whenever the foundation changes. `repo-spec validate`
checks required files and basic structure; it does not decide whether the architecture is correct.

## Reconcile after init (existing `.agents/` or leftover `.agent/`)

`init-workspace.sh` / `init-feature.sh` already run `repo-spec init`. If `.agents/`
already existed (skills, custom agents, notes), those entries stay. After init:

1. Run `./scripts/adlc5 repo-spec reconcile --workspace .`
2. Read the JSON: `adopted`, `skipped_legacy`, `kept_existing`, `leftover_legacy`, `missing`
3. Keep everything in `kept_existing` (especially `.agents/skills/`)
4. Treat `adopted` files as the useful fetch from `.agent/` — review them before trusting `status: draft` or copied `approved` values
5. If `skipped_legacy` lists a destination that exists, the `.agents/` file wins; diff the legacy file only if you know it is newer
6. Fill remaining drafts, then `repo-spec validate`
7. Delete leftover **constitution** files under `.agent/` (`architecture.yaml`, `boundaries.yaml`, `commands.yaml`, `schemas/`) only after validate succeeds
8. Do **not** delete `.agent/skills/` (Antigravity host path) and do **not** merge it into `.agents/skills/`

Useful vs not:

| Source | Action |
|--------|--------|
| `.agent/architecture.yaml`, `boundaries.yaml`, `commands.yaml`, `schemas/task-spec.schema.json` | Adopt into `.agents/` when missing; then remove the legacy copies after review |
| `.agents/skills/` | Keep; ADLC5 project skill links |
| Other files already in `.agents/` | Keep; constitution yaml sits beside them |
| `.agent/skills/` | Leave for Antigravity; not ADLC5 constitution |
| `.adlc5/governance/` | Keep where it is |
| `.agent-cache/` | Generated; gitignored; refresh, do not commit |

`reconcile` never overwrites an existing `.agents/` constitution file and never deletes `.agent/`.

## Repository intelligence

`repo-index` creates `.agent-cache/` and adds it to `.gitignore`. The cache contains
paths and structural facts, never source bodies:

```text
.agent-cache/
  manifest.json
  repo-index.json
  module-map.json
  symbols.json
  dependency-graph.json
  test-map.json
```

```bash
./scripts/adlc5 repo-index build --workspace .
./scripts/adlc5 repo-index refresh --workspace .
./scripts/adlc5 repo-index check --workspace .
```

The initial implementation performs a deterministic full refresh. This keeps the
cache correct across add/change/delete/rename without a persistent database.
Optimize per-file extraction only after measurements justify the extra state.

Commit the `.agents/` constitution and leave `.agent-cache/` ignored. `repo-index check`
returns success when the cache matches the current repository and exit code `3` when
it is missing, malformed, tampered with, or stale; refresh it before planning.

## Retrieval order

1. Read `AGENTS.md` and `.agents/{architecture,boundaries,commands}.yaml`.
2. Read the active feature `spec-handoff.md`.
3. Read `.agent-cache/repo-index.json`, then only matching module, symbol,
   dependency, and test records.
4. Open source files only to resolve remaining uncertainty.

The cache is local structural intelligence, not a privacy filter. Any context sent
to a remote model still needs an allow-list, secret scan, and data-minimization step.

## Focused context and evidence

`adlc5 pack --feature NAME --story-id ID --persona coder --workspace .` assembles
the declared story and acceptance, its code spec (or tiny change record), the spec
handoff, and available repository guidance. It checks an estimated text budget and
blocks when required content is missing. Agents select relevant index records and
inspect source separately; the pack does not automatically include all source or
the complete repository cache. Hidden host prompts and subsequent reads are unknown.

Repository freshness and completion evidence answer different questions.
`repo-index check` validates the structural map; evidence checks and review establish
the selected delivery contract for current inputs. Neither is proof of defect-free
code, production qualification, or measured token savings. The connection across
these mechanisms is the Intelligence claim; comparative outcomes need measurements.
