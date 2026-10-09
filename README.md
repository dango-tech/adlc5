<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/logo-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/brand/logo-light.svg">
  <img alt="ADLC5" src="assets/brand/logo-light.svg" width="480">
</picture>

**Public preview.** ADLC5 has tested workflow contracts; comparative coding-quality
and outside-contributor qualification are still pending.

**ADLC5** is a coding harness for **Specify → Plan → Tasks → Implement**.
The five pillars are **Specify · Plan · Tasks · Implement · Intelligence**.
Four pillars structure delivery. Intelligence connects them to your codebase.
Agent skills handle judgment; one deterministic kernel owns progression and checks.
It aims for repeatable acceptance and failure handling, not identical generated code.

## Quickstart

Required: Git, Bash, Python 3.10+, jq, and a supported agent host for AI delivery.
Consumer checks and kernel tests do not require an AI subscription.

```bash
git clone https://github.com/dango-tech/adlc5.git
cd adlc5
cp config.example.yaml config.yaml
./scripts/install.sh --platform codex  # or your host
./scripts/verify-install.sh --platform codex
```

In your application repository:

```bash
/path/to/adlc5/scripts/init-workspace.sh --project .
/path/to/adlc5/scripts/init-feature.sh --feature my-feature --interaction hitl
```

**Claude Code plugin (no clone needed at runtime):** build the local package with
`python3 scripts/package-plugin.py --out /tmp/adlc5-dist`, start a session with
`claude --plugin-dir /tmp/adlc5-dist/adlc5-plugin-<version>.zip`, then invoke the
`adlc5-setup` skill in your repository. Skills appear as `adlc5:<name>`. See the
[Claude plugin guide](shared/docs/INSTALL.md#claude-code-plugin-local-package).

Then invoke **`@adlc5 for my-feature`**. Use the framework in consumer repositories;
this repository distributes the framework and its portable `dogfood/` example.
See [installation](shared/docs/INSTALL.md) for other hosts and upgrades.

## Start with an existing repository (brownfield)

Run `init-workspace.sh --project .` in your existing application repository before
the first feature. It preserves existing constitution files, creates missing
drafts under `.agents/` and an ADR area under `docs/adr/`, and builds a local,
gitignored `.agent-cache/`. Review the architecture, boundaries, and commands in
`.agents/`, then validate them with:

```bash
/path/to/adlc5/scripts/adlc5 repo-spec validate --workspace .
/path/to/adlc5/scripts/adlc5 repo-index check --workspace .
```

The codebase is **indexed into JSON**, rather than copied into JSON: `manifest.json`,
`repo-index.json`, `module-map.json`, `symbols.json`, `dependency-graph.json`, and
`test-map.json` record the snapshot, file/module structure, supported symbols and
imports, and test locations/matches. The scan covers eligible source files and
workspace manifests across the repository, excluding generated/dependency folders,
symlinks, and recognized secret files. Extraction varies by language; this is
structural context, not a complete semantic model. Agents query relevant records,
then read source to resolve remaining questions.

Feature initialization refreshes the index; after other edits, use
`adlc5 repo-index refresh --workspace .` when the check reports it stale.
Commit reviewed `.agents/` files and ADRs; leave `.agent-cache/` ignored.
For optional team-shared codebase knowledge, add `--with-project-wiki` and review
ingest drafts before promotion. Feature initialization also bootstraps the wiki
when the brownfield repository profile warrants it. See
[repository context](core/guides/repository-context.md) and the
[project wiki workflow](shared/docs/project-wiki.md).

## Four stages, proportionate depth

| Stage | Useful output |
|---|---|
| Specify | Expected behavior, constraints, acceptance, explicit risk assessment |
| Plan | Existing flow to reuse, intended change, boundaries and decisions |
| Tasks | Bounded work units and checkable specs when decomposition helps |
| Implement | Patch, runnable checks, diff review and current completion evidence |

Tiny work keeps decisions in one `change.md`. Standard work keeps a brief
`design/plan.md`; high-risk work retains detailed design, independent critique,
QA and human approval. Knowledge-base and craftsmanship material are pulled in
when a concrete problem needs them.

## Intelligence — the fifth pillar

ADLC5 gathers repository knowledge, gives agents relevant context, and uses
current evidence to guide delivery. Its distinction is the connection across the
lifecycle: repository maps inform planning, reviewed guidance constrains tasks,
focused context packs equip agents, and evidence checks govern progression.

- **Understand:** generate maps of modules, symbols, import dependencies, and tests.
- **Constrain:** retain reviewed architecture, boundaries, and runnable commands.
- **Equip:** assemble bounded story context from requirements and repository guidance.
- **Refresh and verify:** check map freshness and require current completion evidence.

Models supply reasoning; ADLC5 supplies structured knowledge, context, and checks.
Generated maps remain navigation aids; source and reviewed guidance are authoritative.
SOUL is the supporting reasoning discipline across all four stages.
[Repository context and limits](core/guides/repository-context.md) explains the
mechanics. Better code, fewer errors, or lower token costs require comparative measurements.

## What completion establishes

`adlc5 transition TARGET` validates the next step and its required gates.
`adlc5 evidence check` runs consumer-declared commands; review and approval records
are bound to the patch and acceptance/configuration inputs. Relevant edits make
previous evidence stale. Generic `state set` is for metadata, not completion.

`pr-ready` establishes that the selected profile's required checks and review have
passed for current inputs. It does not establish deployment, public availability,
legal clearance, or defect-free production operation. Local records are writable;
this is procedural enforcement, not authentication against a malicious local actor.
See [completion commands and limits](docs/evidence-completion.md).

## Try a real consumer task

```bash
python3 dogfood/consumer/regression.py
python3 scripts/evaluation/run-case.py prepare --case tiny-label \
  --arm candidate --host codex --model YOUR_ACTUAL_MODEL \
  --directory /tmp/adlc5-tiny-label-candidate-1
```

Open the generated `HANDOFF.md` in a fresh host session. The six-case fixture has
independent frozen acceptance tests and a collector that reports missing observations
honestly. See [consumer instructions](dogfood/consumer/README.md) and the
[evaluation contract](docs/evaluation.md). Automated fixture tests are not live
comparative quality results; the pilot and outside-contributor trial remain pending.

## Host support

The contract-test CI matrix covers Ubuntu and macOS; disposable installation smoke
covers Claude skill links and kernel verification, and the Claude Code plugin package
has archive, MCP stdio, bootstrap and hook tests plus a recorded live local session. Codex and Cursor have packaged
adapter/hook tests. Other install adapters remain available but do not imply equal
end-to-end delivery validation. See [cross-platform details](shared/docs/CROSS-PLATFORM.md).
Live delivery/resume qualification must be recorded per host before broader claims.
See [distribution contents](docs/distribution.md) for archive exclusions and publication checks.

## Contribute

```bash
/bin/bash scripts/tests/run-all.sh
python3 scripts/tests/test-portable-install.py
```

Start with a reproducible problem and a focused fix. A new rule, gate or skill should
show the failure it prevents. [CONTRIBUTING.md](CONTRIBUTING.md) names the checks and
consumer scenario expected for each contribution; [GOVERNANCE.md](GOVERNANCE.md)
describes larger changes.

Further reference: [kernel](docs/ADLC5-kernel.md), [skill map](shared/docs/SKILL-MAP.md),
[repository context](core/guides/repository-context.md), [on-demand KB](shared/docs/knowledge-base/README.md),
[current technology sources](core/guides/current-information.md), [license](LICENSE).

Framework version: [core/VERSION](core/VERSION). Persisted state retains schema `3.0`.

## Documentation website

The browsable user docs in `website/docs/` cover overview, installation, quickstart,
lifecycle, Intelligence, and reference. For a local preview:

```bash
python3 -m venv .venv-docs
. .venv-docs/bin/activate
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

See [site maintenance and GitHub Pages setup](docs/documentation-site.md) for builds,
validation, and publication. The workflow validates pull requests and can publish
from the default branch after Pages is configured.
