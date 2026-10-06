# Claude Code token usage collection

**Last verified:** 2026-09-04
**Status:** No API key needed — reads Claude Code's own on-disk transcript.

ADLC5 records exact, provider-reported token counts and the model used for
every completed Claude Code turn into that feature's
`memory/usage-ledger.jsonl`. See [docs/agent-usage.md](agent-usage.md) for how
this fits into the cross-platform, agent-agnostic ledger.

## Why no API key or network call

Claude Code hook payloads don't carry `usage` or `model` fields directly, but
every hook does carry `transcript_path`, and Claude Code already writes
`message.model` and `message.usage` (`input_tokens`, `output_tokens`,
`cache_creation_input_tokens`, `cache_read_input_tokens`) into that JSONL file
for every completed assistant turn — the same counts Anthropic's API returned,
not an estimate. `scripts/claude-usage.py` just reads that file.

## Install

```bash
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app \
  --with-hooks --hooks-platform claude
```

This copies `.claude/settings.json` (wiring `UserPromptSubmit` and `Stop`
hooks to `.claude/hooks/claude-usage.sh`) and the wrapper script itself into
the target project. No `~/.adlc5/*.env` file, no secret, no LaunchAgent.

If the project already has its own `.claude/settings.json` with hooks you
care about, don't run `--with-hooks --hooks-platform claude` blindly — it
overwrites the whole file. Merge the `UserPromptSubmit`/`Stop` entries from
`.claude/settings.json` in this repo into yours by hand instead.

## How binding works

`UserPromptSubmit` extracts the feature name from `@adlc5 for feature-name`
(or `--feature feature-name` in a CLI-style prompt) and binds Claude's stable
`session_id` to that feature/stage/step, the same convention Cursor uses.
`Stop` then reads the transcript, finds every assistant turn not already in
the ledger, and records one entry per turn with its exact tokens and model.

No binding exists yet? The `Stop` hook is a no-op — nothing is recorded until
a `@adlc5 for feature-name` prompt has bound the session at least once.

## Manual bind

```bash
python3 scripts/claude-usage.py bind \
  --workspace /path/to/app --feature feature-name --session-id <claude-session-id>
```

## Sources

- Claude Code hooks reference, `Stop`/`UserPromptSubmit` payload fields:
  <https://docs.claude.com/en/docs/claude-code/hooks>
