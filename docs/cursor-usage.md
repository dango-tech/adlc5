# Cursor token usage collection

**Last verified:** 2026-09-03  
**Status:** Cursor SDK and Cloud Agents APIs are beta; Admin/Organization API is Enterprise-only.

ADLC5 can reconcile official Cursor token counts and billed cost into each
feature's `memory/usage-ledger.jsonl`. Secrets remain in
`~/.adlc5/cursor-usage.env`, outside consumer repositories.

## Cursor has three incompatible API key types

Confirmed 2026-09-03 against a real Enterprise account: these are **not**
interchangeable, regardless of the "Admin" scope label shown in the dashboard.

| Key type | Where created | Works for |
|---|---|---|
| **User API key** (personal) | Dashboard → API (your personal keys page) | Cloud Agent API (`/v1/agents/*`), SDK, headless CLI |
| **Team API key** | Inside a specific Team's own settings — not always exposed to every team member | Admin API `/teams/*` (`filtered-usage-events`, `members`, `spend`) |
| **Organization API key** | Organization-level settings (Enterprise, above teams) | `/organizations/*` (org-pooled counterpart of the above, plus org membership/groups) |

If you only see a "User API Keys" page in your dashboard, you have a personal
key. It returns `401 Invalid Team API Key` / `401 Invalid Organization API Key`
on `/teams/*` and `/organizations/*` — that is expected, not a config bug.
Use `sync-cloud` / `sync-cloud-all` below; `sync` / `sync-all` need a real
Team or Org key from whoever holds that role.

## Configure this machine

```bash
./scripts/install-cursor-usage.sh
chmod 600 ~/.adlc5/cursor-usage.env
```

Fill in at minimum (personal key, works with everyone's account):

```dotenv
CURSOR_API_KEY=crsr_...
```

Add `CURSOR_ADMIN_API_KEY` + `CURSOR_USAGE_EMAIL` only if you have a real Team
or Organization key (see table above) and want `sync`/`sync-all` too.

Then enable hourly reconciliation on macOS:

```bash
./scripts/install-cursor-usage.sh --enable
```

The installer creates `~/Library/LaunchAgents/com.adlc5.cursor-usage.plist`
running `sync-cloud-all` hourly (the path that works with a personal key).
Disable it with:

```bash
./scripts/install-cursor-usage.sh --disable
```

## Enable workspace correlation

Install project hooks in each consumer workspace:

```bash
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app --with-hooks --force
```

The hooks associate `@adlc5 for feature-name` and subsequent
`--feature feature-name` kernel calls with Cursor's stable `conversation_id`
(IDE sessions) or Cloud Agent `id` (`bc-...`). No API key is exposed to hooks
or agent prompts.

## Cloud agents (works with a personal User API key)

Bind a Cloud Agent to a feature once — same command as IDE binding, just pass
the agent's `bc-...` id as the conversation ID:

```bash
./scripts/adlc5 usage cursor bind \
  --workspace /path/to/app --feature feature-name --conversation-id bc-...
```

Then reconcile:

```bash
./scripts/adlc5 usage cursor sync-cloud --workspace /path/to/app --force
./scripts/adlc5 usage cursor sync-cloud-all --force   # all registered workspaces
```

`sync-cloud` polls `GET /v1/agents/{id}/usage` for every bound agent. Usage is
cumulative per run while it's still active, so the collector stores the last
seen totals per `{agent_id, run_id}` in `.adlc5/cursor-usage-sync.json` and
records only the positive delta each poll — a run is never double-counted.

You can also record a specific run directly without binding first:

```bash
./scripts/adlc5 usage cursor cloud \
  --workspace /path/to/app \
  --feature feature-name \
  --agent-id bc-... \
  --run-id run-... \
  --model-id composer-...
```

## IDE Composer sessions (needs a Team or Org Admin key)

```bash
./scripts/adlc5 usage cursor sync --workspace /path/to/app --force
./scripts/adlc5 usage cursor sync-all --force
```

Cursor aggregates Admin/Organization API usage hourly. The collector therefore
polls no more than once per 55 minutes by default, uses a 48-hour overlap for
delayed events, and deduplicates each event before appending it to the ledger.
Without a Team/Org key, IDE session cost stays a self-reported estimate in the
ledger, same as ADLC5's default behavior before this collector existed.

## Sources

- Cursor Admin API, usage event fields and hourly aggregation:
  <https://cursor.com/docs/account/teams/admin-api>
- Cursor Cloud Agents API, per-agent and per-run token usage:
  <https://cursor.com/docs/cloud-agent/api/endpoints>
- Cursor SDK, live run usage and billed `Agent.getUsage()`:
  <https://cursor.com/docs/sdk/typescript>
- Cursor hooks, stable conversation IDs and supported cloud events:
  <https://cursor.com/docs/hooks>
