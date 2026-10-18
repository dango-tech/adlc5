# ADLC5 Pulse

Pulse presents a local, on-demand view of ADLC5 feature progress, recorded evidence, usage coverage, and a suggested next action. It is available in ADLC5 5.1.0 through the shared CLI, a read-only MCP snapshot tool, and the Codex, Claude Code, and Cursor plugin packages.

Pulse reads consumer files. Snapshot, band, handoff, and MCP calls do not run consumer commands, change lifecycle state, write files, or make network requests. `board` is the explicit write operation: it writes a sanitized snapshot and a self-contained offline HTML file under the consumer's ignored `.agent-cache/pulse/` directory. `--open` asks the local browser to open that file.

## Commands

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

After generating the board, `pulse band --cached --feature my-feature` reads a cached feature snapshot. It labels the capture time and says present freshness is unverified. Regenerate the board to refresh the cache. A workspace board also stores one feature cache for each observed feature.

The CLI returns exit 0 for valid empty or partial observations, 2 for invalid workspaces/arguments/unsafe paths, and 1 for unexpected output failures. Machine-readable snapshot JSON is written to stdout; warnings use safe relative source identifiers.

## Reading evidence

Checks and reviews are compared with the canonical ADLC5 input fingerprint. A matching result is current at the time Pulse captured it; a changed fingerprint is stale. Missing fingerprints remain historical. The full `pr-ready` gate is shown separately and only as a recorded local observation when the receipt binds the gate evaluator, canonical input fingerprint, and mutable gate dependencies. Old receipts, unstable capture, changed approval/review/check inputs, changed evaluator, and unverifiable custom/external inputs cannot appear as a current gate pass.

Pulse does not run `pr-ready`. A local gate pass does not establish a pull request, human approval, remote CI, deployment, or production health. Archived feature evidence is historical and is not recomputed against today's workspace.

The next-action label is selected from recorded blockers and current evidence. Pulse does not execute or synthesize arbitrary receipt commands. The handoff output is text for review and does not write a clipboard, issue, comment, or message.

## Usage and limits

Cost is an estimate from explicit host-reported amounts or the existing dated model price table and user override. `known_cost_usd` is an attributable subtotal, not an invoice. `complete_total_usd` remains null because Pulse cannot prove that the ledger contains every session event. Missing or unavailable counters and unpriced models remain unknown; an unavailable row with zero-normalized counters does not become `$0`.

The reader accepts regular files up to 8 MiB, at most 50,000 evidence/usage records per feature and 200 features per workspace. Fingerprinting also has aggregate file/byte/time ceilings. Symlinks and special files in the inspected source set are refused. Incomplete final JSONL lines, malformed rows, changing inputs, or exceeded limits produce partial/unavailable freshness with warnings. Source text, prompts, command output, usernames, and arbitrary metadata are not included in the snapshot.

The board is self-contained, works offline, follows system light/dark mode, and uses the existing ADLC5 icon and charcoal/mint palette. It does not refresh itself: run `board` again and reload the page. Snapshots and boards contain local project metadata; keep them out of public pull requests and release archives.

## Plugin setup

All three plugin packages contain the shared `@adlc5-pulse` skill and `adlc5_pulse` read-only MCP tool. Use the skill or invoke the CLI explicitly to open the local board.

The Claude Code plugin also draws a native Pulse band above the prompt. It takes a fresh, read-only snapshot when a session starts and after each completed turn. The compact band shows the selected feature, lifecycle stage, check and local gate status, and known-cost subtotal. **Review** and **Audit** invoke existing ADLC5 skills, **Board** explicitly writes and opens the offline board, and **Details** expands the captured step, review, usage, time, and suggested next action. Set `ADLC5_FEATURE` in the Claude Code environment to pin one feature when the workspace has several; without a selection, the band names the count instead of choosing arbitrarily. The band does not replace or edit Claude's status-line setting. Claude Code mods are supported in interactive sessions; `claude -p` and Agent SDK sessions keep the skill, MCP, and CLI surfaces.

Codex and Cursor expose the same Pulse snapshot through the skill, read-only MCP tool, and CLI. Their documented plugin surfaces do not currently provide a persistent custom band above the prompt, so they use the existing command/board flow rather than claiming visual parity. Claude Code's native band requires a host version with plugin mods enabled; unsupported or noninteractive sessions retain the skill, MCP, and CLI interfaces.

Host capability references: [Claude Code mod interface](https://code.claude.com/docs/en/plugins/mods/interface), [OpenAI plugin extensions](https://developers.openai.com/plugins/build/extensions), and [Cursor hooks](https://docs.cursor.com/hooks).

Cursor package contents and offline generation are covered by package tests. The actual Cursor IDE install/reload, skill discovery, MCP invocation, consumer-root behavior, and stale-evidence display have not yet been qualified; this remains a live-host acceptance check.

See [kernel commands and MCP](ADLC5-kernel.md), [plugin build and install](agent-plugins.md), and [the GitHub Wiki Pulse guide](https://github.com/dango-tech/adlc5/wiki/Pulse).
