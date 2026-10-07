# Cursor token usage collection

**Optional integration:** API availability and permissions depend on your Cursor
account. Check the linked vendor documentation before configuring access.

ADLC5 can reconcile official Cursor token counts and billed cost into each
feature's `memory/usage-ledger.jsonl`. Secrets remain in
`~/.adlc5/cursor-usage.env`, outside consumer repositories.

## Collector credentials

The collector uses `CURSOR_API_KEY` for Cloud Agent requests and
`CURSOR_ADMIN_API_KEY` plus `CURSOR_USAGE_EMAIL` for Admin usage requests.
Use credentials authorized for the selected endpoint; a personal key does not
imply administrative access. Do not place credentials in project files or prompts.

## Configure this machine

```bash
./scripts/install-cursor-usage.sh
chmod 600 ~/.adlc5/cursor-usage.env
```

For Cloud Agent reconciliation, fill in:

```dotenv
CURSOR_API_KEY=crsr_...
```

Add `CURSOR_ADMIN_API_KEY` + `CURSOR_USAGE_EMAIL` only if your account has administrative
usage API access and you want `sync`/`sync-all` too.

Optionally enable hourly reconciliation on macOS (makes network requests):

```bash
./scripts/install-cursor-usage.sh --enable
```

The installer creates `~/Library/LaunchAgents/com.adlc5.cursor-usage.plist`
running `sync-cloud-all` hourly.
Disable it with:

```bash
./scripts/install-cursor-usage.sh --disable
```

## Enable workspace correlation

Install project hooks in each consumer workspace:

```bash
/path/to/adlc5/scripts/init-workspace.sh --project /path/to/app --with-hooks
```

The hooks associate `@adlc5 for feature-name` and subsequent
`--feature feature-name` kernel calls with Cursor's stable `conversation_id`
(IDE sessions) or Cloud Agent `id` (`bc-...`). No API key is exposed to hooks
or agent prompts.

## Cloud Agent reconciliation

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

## IDE session reconciliation (requires Admin API access)

```bash
./scripts/adlc5 usage cursor sync --workspace /path/to/app --force
./scripts/adlc5 usage cursor sync-all --force
```

The collector polls no more than once per 55 minutes by default, uses a 48-hour overlap for
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
