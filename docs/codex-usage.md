# Codex CLI token usage collection

**Last verified:** 2026-09-17
**Status:** Experimental / version-sensitive. Rollout token-count parsing is verified against real output; project-level `.codex/hooks.json` loading is **not independently confirmed working** on every Codex CLI build — see [Known issue: hooks may not fire](#known-issue-hooks-may-not-fire) before relying on this.

ADLC5 records exact, provider-reported token counts and the model used for
every completed Codex CLI turn into that feature's
`memory/usage-ledger.jsonl`. See [docs/agent-usage.md](agent-usage.md) for how
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
   — the shape actually observed on a real Codex CLI 0.144.0-alpha.4 rollout.
   Carries **no** `turn_id`/`response_id` at all — only a session-wide
   `info.last_token_usage` delta and `info.total_token_usage` running total.
   The collector falls back to the most recent one in the file when (1) is
   absent, since `Stop` fires right after that turn's final update.

Codex ships fast-moving alpha releases (10+ minor versions in the two weeks
between this doc's prior and current verification), so which shape a given
install actually writes is not guaranteed to stay fixed — hence checking both.

## Known issue: hooks may not fire

A direct smoke test against Codex CLI 0.144.0-alpha.4, using the exact
`.codex/hooks.json` structure this repo installs, produced **no**
`SessionStart` or `UserPromptSubmit` hook invocation at all — even with
`--dangerously-bypass-hook-trust` set (which only bypasses the per-hook
review-and-trust step, not project trust itself). Per the official docs,
project-local hooks load only when the project's `.codex/` layer is
**trusted** — a separate, earlier gate than the per-hook `/hooks` review step
below. If your hooks aren't firing:

1. Confirm the project directory itself is trusted by Codex (not just the
   individual hook definitions) — check whatever mechanism your Codex CLI
   version uses to establish project trust before `.codex/hooks.json` is
   even considered.
2. Run `/hooks` in Codex CLI and confirm `UserPromptSubmit`/`Stop`/
   `SubagentStop` from `.codex/hooks/codex-usage.sh` actually appear in the
   list, not just that they're trusted.
3. As a smoke test, run `@adlc5 for some-feature` once, then check whether
   `.adlc5/some-feature/memory/codex-usage-bindings.jsonl` exists — if it
   doesn't, the `UserPromptSubmit` hook never fired on your build.

This is a real, version-sensitive gap, not a hypothetical — treat Codex
support as best-effort until you've confirmed hooks actually invoke on your
installed version.

## Install

```bash
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app \
  --with-hooks --hooks-platform codex
```

This copies `.codex/hooks.json` (wiring `UserPromptSubmit`, `Stop`, and
`SubagentStop` to `.codex/hooks/codex-usage.sh`) and the wrapper script into
the target project.

After install, run `/hooks` inside Codex CLI once to review and trust the new
hook — Codex hashes each non-managed command hook and skips it until you
explicitly trust it, even though the `hooks` feature itself is on by default.

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
