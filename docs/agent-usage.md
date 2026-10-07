# Agent-agnostic token usage collection

ADLC5 tracks token spend and model choice per feature in a single normalized
ledger — `.adlc5/{feature}/memory/usage-ledger.jsonl` — no matter which AI
coding agent produced the work. `usage-ledger.py` and `adlc5 usage summary` /
`adlc5 usage fleet` read every entry through the same schema
(`platform`, `model_id`, `source`, `tokens.{input,output,cache_creation,
cache_read,total}`), so a worktree opened from Cursor, Claude Code, or Codex
CLI rolls up into one number instead of three incompatible ones.

## How the normalization works

1. Each platform gets its own thin collector script
   (`scripts/cursor-usage.py`, `scripts/claude-usage.py`,
   `scripts/codex-usage.py`) that knows that platform's hook payload shape and
   where to find exact token counts.
2. All three share `scripts/lib/agent_usage_common.py` for the
   platform-independent parts: binding a conversation/session/turn ID to an
   ADLC5 `feature`/`stage`/`step`, deduplicating already-recorded events, and
   writing normalized entries via `usage-ledger.py record --platform ...`.
3. Installation is what makes this "smart enough" per agent: each platform's
   hook config only exists under its own directory (`.cursor/`, `.claude/`,
   `.codex/`), and `init-workspace.sh --with-hooks` only installs the
   platform(s) you ask for — see [Installation](#installation) below.

## Capability matrix

| Platform | Exact tokens? | Source of tokens | Model field | Collector | Docs |
|---|---|---|---|---|---|
| Cursor Cloud Agents | Yes | `GET /v1/agents/{id}/usage` (delta-tracked) | `model_id` on the binding | `scripts/cursor-usage.py` | [docs/cursor-usage.md](cursor-usage.md) |
| Cursor IDE sessions | Requires Admin API access | Admin API `filtered-usage-events` | hook `model`/`model_id` | `scripts/cursor-usage.py` | [docs/cursor-usage.md](cursor-usage.md) |
| Claude Code | Yes | `message.usage` in the on-disk transcript JSONL | `message.model` in the transcript | `scripts/claude-usage.py` | [docs/claude-usage.md](claude-usage.md) |
| Codex CLI | When supported records and hooks are available | `token_usage_record` or `event_msg`/`token_count` in the on-disk rollout JSONL (both checked) | `Stop`/`SubagentStop` hook `model` field | `scripts/codex-usage.py` | [docs/codex-usage.md](codex-usage.md) |

Collectors depend on host hook delivery and supported usage records. Confirm
collection in your own installation; missing records mean unavailable usage,
not zero spend. Cursor API permissions vary by account. Codex hook delivery
is version-sensitive; see [the verification steps](codex-usage.md#verify-hook-delivery).
Other hosts can use manual `adlc5 usage record` entries.

## Installation

```bash
# Default: Cursor hooks only (back-compat with existing installs)
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app --with-hooks

# Pick platforms explicitly — comma-separated or "all"
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app --with-hooks --hooks-platform claude
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app --with-hooks --hooks-platform cursor,codex
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app --with-hooks --hooks-platform all
```

`--hooks-platform` only controls which hook config gets copied
(`.cursor/hooks.json`, `.claude/settings.json`, `.codex/hooks.json`, plus each
one's `hooks/*.sh` wrapper). Installing for one platform never creates the
other platforms' directories, so a Claude Code-only repo doesn't end up with
an inert `.cursor/hooks.json` it will never run, and vice versa.

The same per-platform hook configs also carry the fail-fast engagement gate,
which warns when a session edits feature-sized work with no ADLC5 feature
engaged — see [docs/engagement-gate.md](engagement-gate.md).

## Sources

- Claude Code hooks reference: <https://docs.claude.com/en/docs/claude-code/hooks>
- Codex CLI hooks reference: <https://developers.openai.com/codex/hooks>
- Cursor hooks reference: <https://cursor.com/docs/hooks>
