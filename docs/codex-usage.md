# Codex CLI token usage collection

**Status:** Experimental / version-sensitive. Rollout token-count parsing is verified against real output; project-level `.codex/hooks.json` loading is **not independently confirmed working** on every Codex CLI build — see [Verify hook delivery](#verify-hook-delivery) before relying on this.

When hooks deliver supported usage records, ADLC5 records provider-reported
token counts and the model in the feature's `memory/usage-ledger.jsonl`. See [docs/agent-usage.md](agent-usage.md) for how
this fits into the cross-platform, agent-agnostic ledger.

## Why no API key or network call

Codex CLI's `Stop`/`SubagentStop` hook payloads carry `model` directly, and
every turn-scoped hook also carries `transcript_path` — the on-disk rollout
JSONL. Two real rollout item shapes carry token counts; `scripts/codex-usage.py`
tries both, in this order:

1. `{"type": "token_usage_record", "payload": {turn_id, response_id, usage,
   ...}}` — durably written per completed turn on some Codex CLI versions
   (`codex-rs` `RolloutItemWire::TokenUsageRecord`, structs
   `TokenUsageRecord`/`TokenUsage`). Matched by `turn_id`.
2. `{"type": "event_msg", "payload": {"type": "token_count", "info": {...}}}`
   — session-level fallback.
   Carries **no** `turn_id`/`response_id` at all — only a session-wide
   `info.last_token_usage` delta and `info.total_token_usage` running total.
   The collector falls back to the most recent one in the file when (1) is
   absent, since `Stop` fires right after that turn's final update.

## Verify hook delivery

Hook support and project trust settings depend on the installed Codex version.
Confirm the installed usage hooks are loaded and allowed using the vendor
documentation below. After invoking `@adlc5 for some-feature`, check for
`.adlc5/some-feature/memory/codex-usage-bindings.jsonl`. If it is absent,
automatic collection has not been demonstrated; use manual usage recording
until hook delivery works. Never interpret a missing ledger as zero usage.

## Install

```bash
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app \
  --with-hooks --hooks-platform codex
```

This copies `.codex/hooks.json` (wiring `UserPromptSubmit`, `Stop`, and
`SubagentStop` to `.codex/hooks/codex-usage.sh`) and the wrapper script into
the target project.

After install, review and trust the hooks using the mechanism supported by your
installed Codex version. Confirm delivery as described above.

If the project already has its own `.codex/hooks.json`, don't run
`--with-hooks --hooks-platform codex` blindly — it overwrites the whole file.
Merge the `UserPromptSubmit`/`Stop`/`SubagentStop` entries from
`.codex/hooks.json` in this repo into yours by hand instead.

## How binding works

`UserPromptSubmit` extracts the feature name from the `prompt` field
(`@adlc5 for feature-name` or `--feature feature-name`) and binds Codex's
`session_id` to that feature/stage/step, the same convention Cursor and
Claude Code use. `Stop`/`SubagentStop` then look up that turn's usage (see
[Why no API key or network call](#why-no-api-key-or-network-call) for the two
shapes tried) and record one ledger entry with its exact tokens and model.
`SubagentStop` is wired to the same collector path as `Stop` — both carry the
same `transcript_path`/`turn_id`/`model` shape.

No binding exists yet? The hook is a no-op — nothing is recorded until a
`@adlc5 for feature-name` prompt has bound the session at least once.

## Manual bind

```bash
python3 scripts/codex-usage.py bind \
  --workspace /path/to/app --feature feature-name --session-id <codex-session-id>
```

## Sources

- Codex CLI hooks reference, config shape, default-on status, and hook trust
  requirement: <https://developers.openai.com/codex/hooks>
