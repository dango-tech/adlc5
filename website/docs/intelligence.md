# Intelligence

**Intelligence is the fifth pillar of ADLC5:** its ability to gather repository
knowledge, give agents relevant context, and use evidence to guide delivery.

**Specify · Plan · Tasks · Implement · Intelligence.** The first four are
delivery stages; Intelligence connects them to your codebase across all four.

## What makes the claim concrete

| Capability | Mechanism | Delivery role |
| --- | --- | --- |
| Repository understanding | Generated module, symbol, dependency, and test maps in `.agent-cache/` | Navigate an existing codebase before choosing a change. |
| Persistent guidance | Reviewed `AGENTS.md`, `.agents/` constitution, and architecture decisions | Carry constraints and commands across sessions. |
| Focused context | Story context packs containing acceptance, specs, and repository guidance | Give an agent bounded work with explicit expectations. |
| Evidence-based progression | Freshness checks, acceptance locks, runnable checks, and recorded review | Require current evidence before advancing or claiming completion. |

The differentiator is the connection: repository knowledge informs planning,
reviewed boundaries shape tasks, context packs equip implementation, and
current evidence governs completion. Models supply reasoning; ADLC5 supplies
structured knowledge, context, and deterministic checks.

SOUL is the supporting reasoning discipline: preserve written acceptance, use
existing knowledge, defer unforced decisions, own implementation boundaries,
and test failure paths. Its five guards remain advisory; gates enforce the
selected delivery contract. See the [lifecycle](lifecycle.md).

## Example: change an existing export flow

1. **Specify:** record the requested export behavior and observable acceptance.
2. **Plan:** read reviewed architecture and boundaries, check the index, then use
   module, symbol, dependency, and test records to locate the export flow. Inspect
   source to confirm the map and choose the existing code to reuse.
3. **Tasks:** declare affected files, tests, dependencies, and acceptance in bounded
   stories. Lock acceptance definitions before implementation.
4. **Implement:** assemble the story context pack, change the declared code, run
   consumer checks, and obtain the required independent review. Relevant edits
   invalidate earlier completion evidence.

Intelligence supports each step. The example illustrates the intended workflow;
it is not a measured quality or cost result.

## Generate and use repository context

For an existing repository, initialize once before the first feature:

```bash
/path/to/adlc5/scripts/init-workspace.sh --project .
```

Initialization preserves existing constitution files, creates missing drafts and
an ADR area under `docs/adr/`, and builds the local JSON index. Run from your
application repository, using your installed framework path:

```bash
/path/to/adlc5/scripts/adlc5 repo-spec init --workspace .
/path/to/adlc5/scripts/adlc5 repo-spec validate --workspace .
/path/to/adlc5/scripts/adlc5 repo-index build --workspace .
/path/to/adlc5/scripts/adlc5 repo-index check --workspace .
```

Initialization creates missing guidance as drafts. Review architecture, boundaries,
and commands before treating them as approved intent. Commit reviewed guidance;
keep generated `.agent-cache/` and feature `.adlc5/` state untracked.

The codebase is indexed into JSON, not copied wholesale into JSON:

| Artifact in `.agent-cache/` | Contents |
| --- | --- |
| `manifest.json` | Snapshot fingerprint and generated artifact list |
| `repo-index.json` | Repository summary, languages, and modules |
| `module-map.json` | Source and test files grouped by module |
| `symbols.json` | Supported declarations with file paths and line numbers |
| `dependency-graph.json` | Extracted import edges |
| `test-map.json` | Test locations and heuristic source/test matches |

The scan covers eligible source files and workspace manifests. It excludes
generated/dependency folders, symlinks, and recognized secret files. Feature
initialization refreshes the index; after other edits, check freshness explicitly.

`repo-index check` returns exit code `3` for missing, malformed, tampered, or stale
cache data. Refresh it before planning:

```bash
/path/to/adlc5/scripts/adlc5 repo-index refresh --workspace .
/path/to/adlc5/scripts/adlc5 pack --feature my-feature --story-id US-001 --persona coder --workspace .
```

The pack command requires an initialized feature and a declared story/spec
(or a tiny change record). It assembles required context and checks its estimated
budget; it does not automatically discover all relevant source. Agents select
matching index records and inspect source separately.

## Optional reviewed project wiki

For team-shared knowledge, initialize with `--with-project-wiki`, then ingest:

```bash
/path/to/adlc5/scripts/wiki/ingest-repo.sh --workspace .
```

Ingest creates draft entity stubs and a source manifest. Humans review evidence
before promoting material to `wiki/entities/`. Feature initialization also
bootstraps this optional wiki when the brownfield repository profile warrants it.
See the [project wiki guide](https://github.com/dango-tech/adlc5/blob/main/shared/docs/project-wiki.md).

## Limits of the claim

- Generated maps contain structural facts and paths, not source bodies or a
  complete semantic model. Extraction depth varies by language; import edges and
  test associations are navigation clues, not proof of complete runtime behavior.
- Repository constitution validation checks structure. Human review establishes
  intent; neither a generated draft nor a successful validation approves architecture.
- Context budgets estimate supplied text. Hidden host prompts and later source
  reads remain unknown overhead.
- Local records are writable. Gates enforce a workflow, not protection against
  an actor who can rewrite local evidence or Git refs.
- Better code, fewer errors, and lower token costs need comparative measurements.
  These capabilities alone do not establish those outcomes.

For implementation contracts, see [repository context](https://github.com/dango-tech/adlc5/blob/main/core/guides/repository-context.md)
and [evidence-backed completion](https://github.com/dango-tech/adlc5/blob/main/docs/evidence-completion.md).
