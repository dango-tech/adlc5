# ADLC5 Pulse

Pulse presents a local, on-demand view of ADLC5 feature progress, recorded evidence, usage coverage, and a suggested next action. It is available in ADLC5 5.1.0 through the shared CLI, a read-only MCP snapshot tool, and the Codex, Claude Code, and Cursor plugin packages.

Pulse reads consumer files. Snapshot, band, handoff, and MCP calls do not run consumer commands, change lifecycle state, write files, or make network requests. `board` is the explicit write operation: every invocation writes the shared offline page at `~/.adlc5/pulse/board.html`. Derived feature caches live under `~/.adlc5/pulse/workspaces/<workspace-hash>/`; no new Pulse files are written into consumer worktrees. `--open` opens that shared page.

## Views

The shared board opens on **Projects**, one application card per Git repository
identity. Linked worktrees share a project; unrelated repositories with the same
folder name do not. Project detail lists its workflows with active/archive filters,
worktrees, agent badges and settings links. Workflow links open one delivery path
with its evidence and next action, without the global inventories above it.
**Activity** provides separate session/attempt views, search and 25-row pagination.
**Settings** provides read-only machine/project/worktree configuration with source
and override history. See [shared home and settings](shared-home.md).

Hash routes support direct links and browser Back/Forward while remaining offline:
`#projects`, `#project/<id>`, `#workflow/<id>`, `#activity`, `#settings`.
The existing workspace/feature Board action opens the selected workflow; the
all-projects command opens Projects. Capture time and coverage remain explicit.

## Commands

### All projects and historical sessions

```bash
./scripts/adlc5 pulse board --all-projects --open
./scripts/adlc5 pulse board --all-projects --root /path/to/other/projects --open
```

The global board lives at `~/.adlc5/pulse/board.html`. It reuses the same
Pulse cards and adds searchable inventories of feature snapshots, native host
sessions with explicit ADLC5 request/tool evidence, and runner attempts. Standard
roots are `~/SourceCode/Github`, `~/.codex/worktrees`, and `~/Documents/Codex`;
additional `--root` directories are remembered in the private local root registry.
Nested worktrees and archived features are included. Codex active/archived,
Claude Code and Cursor JSONL transcript inventories are scanned locally. Other
hosts appear through retained runner results. No raw prompts or command output
are included, and nothing is uploaded. Generated global files have private modes.

This is a snapshot of discovered sources, not proof of complete history: deleted
or inaccessible records, provider-only history and unsupported transcript formats
cannot be recovered automatically. Coverage warnings remain visible. Native
session token subtotals cover entire conversations, not just ADLC5 work; they may
overlap fork prefixes and are not added to feature ledgers. Cost and independent
outcomes stay unmeasured without attributable evidence. Feature snapshots,
sessions and attempts overlap and must not be added as a single run count.
Regenerate with the same command and reload the file to include new runs.

### Agent context and existing pages

Workspace and feature rows display distinct labeled icons for Claude Code, Codex,
Cursor and Hermes Agent. All hosts observed on the exact same resolved worktree
appear together. Attribution comes from explicit ADLC5 native-session evidence,
runner attempt journals, or a caller identifying itself with `board --workspace .
--host claude|codex|cursor|hermes`. Claude's Board action supplies its host automatically.
This means **observed usage**, not a live process or proof of simultaneous activity.
Matching uses the full worktree identity, never just the repository basename;
missing or unresolvable host attribution stays unknown.

Old worktree-local HTML pages and the earlier `~/.config/adlc5/pulse/board.html`
are historical snapshots. They are not moved or deleted. The first central refresh
reads the earlier global root registry and regenerates from source records.
Update the plugin and use its Board action or the current CLI to open the new page.
Feature lifecycle state remains in the consumer's `.adlc5/`; only derived Pulse
reports and caches are centralized. Worktree removal therefore does not erase the
central cache, but a fresh scan cannot recover deleted source history.

### One workspace

Run from a consumer workspace, or provide `--workspace`:

```bash
./scripts/adlc5 pulse snapshot --workspace .
./scripts/adlc5 pulse snapshot --workspace . --feature my-feature
./scripts/adlc5 pulse band --workspace . --feature my-feature
./scripts/adlc5 pulse board --workspace .
./scripts/adlc5 pulse board --workspace . --feature my-feature --open
./scripts/adlc5 pulse handoff --workspace . --feature my-feature
```

Archived features use their archive directory ID to distinguish them from an active feature with the same label:

```bash
./scripts/adlc5 pulse snapshot --workspace . --archive-id my-feature-20261017
```

The workspace/feature arguments select the initial feature in the shared board;
they do not produce a separate HTML page. After generating it,
`pulse band --cached --feature my-feature` and the optional status-line adapter
read that workspace's central feature cache. They label freshness as unverified.
Regenerate the board to refresh the cache.

The CLI returns exit 0 for valid empty or partial observations, 2 for invalid workspaces/arguments/unsafe paths, and 1 for unexpected output failures. Machine-readable snapshot JSON is written to stdout; warnings use safe relative source identifiers.

## Reading evidence

Checks and reviews are compared with the canonical ADLC5 input fingerprint. A matching result is current at the time Pulse captured it; a changed fingerprint is stale. Missing fingerprints remain historical. The full `pr-ready` gate is shown separately and only as a recorded local observation when the receipt binds the gate evaluator, canonical input fingerprint, and mutable gate dependencies. Old receipts, unstable capture, changed approval/review/check inputs, changed evaluator, and unverifiable custom/external inputs cannot appear as a current gate pass.

Pulse does not run `pr-ready`. A local gate pass does not establish a pull request, human approval, remote CI, deployment, or production health. Archived feature evidence is historical and is not recomputed against today's workspace.

The next-action label is selected from recorded blockers and current evidence. Pulse does not execute or synthesize arbitrary receipt commands. The handoff output is text for review and does not write a clipboard, issue, comment, or message.

## Usage and limits

Cost is an estimate from explicit host-reported amounts or the existing dated model price table and user override. `known_cost_usd` is an attributable subtotal, not an invoice. `complete_total_usd` remains null because Pulse cannot prove that the ledger contains every session event. Missing or unavailable counters and unpriced models remain unknown; an unavailable row with zero-normalized counters does not become `$0`.

### Savings and quality on the card and board

Pulse now displays **outcome success**, **projected cost savings**, **escaped defects**, and **rework**. Without complete evidence the card and board say **Not measured**. Outcome success is the evaluator's quality floor, not an AI accuracy score or a count of passing unit tests. The board includes the observed successful/total run count and a 95% Wilson interval for that recorded proportion; the interval assumes independent observations and does not establish general coding accuracy.

Pulse reads the existing evaluator's three JSONL exports from `.adlc5/<feature>/evaluation/telemetry.jsonl`, `usage.jsonl`, and `outcomes.jsonl`. Copy actual collected records there from `scripts/evaluation/run-case.py collect`, preserving distinct run IDs. Several runs can be concatenated in each corresponding file. These local files are optional, remain ignored with the feature tree, and are never uploaded by Pulse. The regular usage ledger alone cannot establish quality or savings.

Every outcome needs the existing evaluation contract's explicit fields (`anchors_passed`, `regression_passed`, `quality_gates_passed`, `anchor_changed`, `rework`, `human_rejected`, and a completed observation window's `escaped_defects`). Telemetry and usage must correlate by `run_id` and `node_id`. Unknown outcomes, malformed/truncated sources, duplicate outcomes or identical usage records, and missing accounting withhold measured percentages. A changed capture withholds metrics too.

For a cost comparison, outcomes additionally carry `case_id`, `comparison_id`, and a `profile` of `direct:<profile>` or `candidate:<profile>`, for example `direct:tiny` and `candidate:tiny`. Assign the same `comparison_id` only to runs with the same frozen task, starting repository revision, acceptance/regression checks, host/model, budgets, and observation window. This ID is the experiment owner's comparability declaration; Pulse cannot independently establish that the experiments were controlled. Do not mix fixture/synthetic results with live evidence.

Savings require equal actual repetitions in both arms for every case, every recorded run passing the quality floor, explicit finite nonnegative `cost_usd` on every usage entry, and a positive direct-agent baseline. The displayed percentage is `100 × (direct spend − candidate spend) / direct spend` across matched cases. Negative savings remain negative and explicit zero cost stays zero. The board shows matched-case count and the observed case range; that range is descriptive, not a confidence interval. This is an observed comparison used to inform a projection, not a promise of future savings. Missing or incomparable evidence stays **Not measured**. Baseline-only, token-only, and estimated-cost records can inform outcome success when valid, but cannot produce this comparison.

Telemetry collection and feedback submission are separate from this read-only display. Pulse neither enables consent nor sends evaluation records to a server.

The reader accepts regular files up to 8 MiB, at most 50,000 evidence/usage records per feature and 200 features per workspace. Fingerprinting also has aggregate file/byte/time ceilings. Symlinks and special files in the inspected source set are refused. Incomplete final JSONL lines, malformed rows, changing inputs, or exceeded limits produce partial/unavailable freshness with warnings. Source text, prompts, command output, usernames, and arbitrary metadata are not included in the snapshot.

The board is self-contained, works offline, follows system light/dark mode, and uses the existing ADLC5 icon and charcoal/mint palette. It does not refresh itself: run `board` again and reload the page. Snapshots and boards contain local project metadata; keep them out of public pull requests and release archives.

## Plugin setup

All three plugin packages contain the shared `@adlc5-pulse` skill and `adlc5_pulse` read-only MCP tool. Use the skill or invoke the CLI explicitly to open the local board.

The Claude Code plugin also draws a native Pulse band above the prompt. It takes a fresh, read-only snapshot when a session starts and after each completed turn. The compact band shows the selected feature, lifecycle stage, check and local gate status, known-cost subtotal, observed savings, and evaluated outcome success with its run count. **Review** and **Audit** invoke existing ADLC5 skills, **Board** explicitly writes and opens the offline board, and **Details** expands the captured step, review, usage, time, escaped defects, rework, metric limitations, and suggested next action. Set `ADLC5_FEATURE` in the Claude Code environment to pin one feature when the workspace has several; without a selection, the band names the count instead of choosing arbitrarily. The band does not replace or edit Claude's status-line setting. Claude Code mods are supported in interactive sessions; `claude -p` and Agent SDK sessions keep the skill, MCP, and CLI surfaces.

Codex and Cursor expose the same Pulse snapshot through the skill, read-only MCP tool, and CLI. Their documented plugin surfaces do not currently provide a persistent custom band above the prompt, so they use the existing command/board flow rather than claiming visual parity. Claude Code's native band requires a host version with plugin mods enabled; unsupported or noninteractive sessions retain the skill, MCP, and CLI interfaces.

Host capability references: [Claude Code mod interface](https://code.claude.com/docs/en/plugins/mods/interface), [OpenAI plugin extensions](https://developers.openai.com/plugins/build/extensions), and [Cursor hooks](https://docs.cursor.com/hooks).

Cursor package contents and offline generation are covered by package tests. The actual Cursor IDE install/reload, skill discovery, MCP invocation, consumer-root behavior, and stale-evidence display have not yet been qualified; this remains a live-host acceptance check.

See [kernel commands and MCP](ADLC5-kernel.md), [plugin build and install](agent-plugins.md), and [the GitHub Wiki Pulse guide](https://github.com/dango-tech/adlc5/wiki/Pulse).

## Live desktop card smoke

On 2026-10-18, the Pulse card was exercised in the local Code tab of Claude Desktop 2.42304.0 on macOS, using a disposable workspace explicitly labeled as synthetic UI data. The test confirmed populated rendering, Details expand/collapse, Review dispatch to `craftsmanship-code-review`, Audit dispatch to `qa`, selected-feature board/cache generation, and turn-complete refresh from measured values to **Not measured** when evaluation exports were held aside, then back when restored. It also confirmed coexistence with Ponytail's band.

The test found and fixed plugin-root resolution and refresh lifetime issues: the mod now uses `$.plugin.root`, invokes the Python kernel directly, and awaits refresh inside its lifecycle hook. Desktop upload/directory builds omit top-level PATH executables with `--claude-hosted`. The test used fixture-only review/audit requests; it does not establish a real application's QA clearance, actual cost savings, or general accuracy. Cursor live qualification remains pending.
