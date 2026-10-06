#!/usr/bin/env python3
"""Collect official Cursor token usage into ADLC5 feature ledgers."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import agent_usage_common as common  # noqa: E402

PLATFORM = "cursor"
CLOUD_PLATFORM = "cursor-cloud"
ROOT = common.ROOT
LEDGER = common.LEDGER
DEFAULT_CONFIG = Path.home() / ".adlc5" / "cursor-usage.env"
DEFAULT_ADMIN_URL = "https://api.cursor.com/teams/filtered-usage-events"
DEFAULT_CLOUD_URL = "https://api.cursor.com/v1/agents"
SYNC_STATE = Path(".adlc5/cursor-usage-sync.json")
MIN_SYNC_INTERVAL_MS = 55 * 60 * 1000
SYNC_OVERLAP_MS = 48 * 60 * 60 * 1000
CLOUD_USAGE_FIELDS = (
    "inputTokens",
    "outputTokens",
    "cacheWriteTokens",
    "cacheReadTokens",
    "totalTokens",
)

now_ms = common.now_ms
write_json = common.write_json
append_jsonl = common.append_jsonl
load_jsonl = common.load_jsonl
load_state = common.load_state
parse_int = common.parse_int
extract_feature = common.extract_feature
usage_ledger_paths = common.usage_ledger_paths
ledger_event_ids = common.ledger_event_ids


def read_config(path: Path = DEFAULT_CONFIG) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Cursor usage config not found: {path}. "
            "Run ./scripts/install-cursor-usage.sh first."
        )
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise ValueError(f"Cursor usage config must have mode 0600: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if not separator or not key.strip():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def bind_usage(
    workspace: Path,
    feature: str,
    conversation_id: str,
    *,
    model_id: str | None = None,
    bound_at_ms: int | None = None,
) -> dict[str, Any]:
    return common.bind_usage(
        PLATFORM, workspace, feature, conversation_id, model_id=model_id, bound_at_ms=bound_at_ms
    )


def discover_bindings(workspace: Path) -> list[dict[str, Any]]:
    return common.discover_bindings(PLATFORM, workspace)


def select_binding(
    bindings: list[dict[str, Any]], event_timestamp_ms: int
) -> dict[str, Any] | None:
    return common.select_binding(bindings, event_timestamp_ms)


def register_workspace(workspace: Path) -> None:
    common.register_workspace(PLATFORM, workspace)


def registered_workspaces() -> list[Path]:
    return common.registered_workspaces(PLATFORM)


def event_fingerprint(event: dict[str, Any]) -> str:
    for key in ("id", "eventId", "usageEventId", "usageUuid"):
        value = event.get(key)
        if value:
            return hashlib.sha256(f"{key}:{value}".encode("utf-8")).hexdigest()
    stable_event = {
        key: event.get(key)
        for key in (
            "timestamp",
            "conversationId",
            "model",
            "tokenUsage",
            "chargedCents",
            "cursorTokenFee",
            "isChargeable",
            "isHeadless",
        )
        if key in event
    }
    canonical = json.dumps(stable_event, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_event(
    workspace: Path,
    binding: dict[str, Any],
    event: dict[str, Any],
    fingerprint: str,
    event_timestamp_ms: int,
) -> None:
    usage = event["tokenUsage"]
    extra = {
        "cursor_usage_event_id": fingerprint,
        "conversation_id": event.get("conversationId"),
        "event_timestamp_ms": event_timestamp_ms,
        "charged_cents": event.get("chargedCents"),
        "model_cost_cents": usage.get("totalCents"),
        "cursor_token_fee_cents": event.get("cursorTokenFee"),
        "is_chargeable": event.get("isChargeable"),
        "is_headless": event.get("isHeadless"),
    }
    common.record_usage(
        workspace=workspace,
        feature=str(binding["feature"]),
        model_id=str(event.get("model") or binding.get("model_id") or "unknown"),
        platform=PLATFORM,
        source="api",
        input_tokens=int(usage.get("inputTokens", 0) or 0),
        output_tokens=int(usage.get("outputTokens", 0) or 0),
        cache_creation_tokens=int(usage.get("cacheWriteTokens", 0) or 0),
        cache_read_tokens=int(usage.get("cacheReadTokens", 0) or 0),
        run_id=str(event.get("conversationId") or ""),
        stage=binding.get("stage"),
        step=binding.get("step"),
        extra=extra,
    )


def ingest_events(workspace: Path, events: list[dict[str, Any]]) -> dict[str, int]:
    bindings_by_conversation: dict[str, list[dict[str, Any]]] = {}
    for binding in discover_bindings(workspace):
        conversation_id = binding.get("conversation_id")
        if conversation_id:
            bindings_by_conversation.setdefault(str(conversation_id), []).append(binding)

    known = ledger_event_ids(workspace)
    recorded = skipped = 0
    for event in events:
        usage = event.get("tokenUsage")
        conversation_id = event.get("conversationId")
        if not isinstance(usage, dict) or not conversation_id or not event.get("timestamp"):
            skipped += 1
            continue
        event_timestamp_ms = parse_int(event.get("timestamp"))
        if event_timestamp_ms is None:
            skipped += 1
            continue
        fingerprint = event_fingerprint(event)
        if fingerprint in known:
            skipped += 1
            continue
        binding = select_binding(
            bindings_by_conversation.get(str(conversation_id), []),
            event_timestamp_ms,
        )
        if not binding:
            skipped += 1
            continue
        record_event(workspace, binding, event, fingerprint, event_timestamp_ms)
        known.add(fingerprint)
        recorded += 1
    return {"recorded": recorded, "skipped": skipped}


def redact_secret(value: str, secret: str) -> str:
    return value.replace(secret, "[REDACTED]") if secret else value


def api_request(url: str, key: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
    credentials = base64.b64encode(f"{key}:".encode("utf-8")).decode("ascii")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method="POST" if body is not None else "GET",
        headers={
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "adlc5-cursor-usage/1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        detail = redact_secret(redact_secret(detail, key), credentials)
        raise RuntimeError(f"Cursor usage API returned HTTP {error.code}: {detail}") from error
    if not isinstance(value, dict):
        raise RuntimeError("Cursor usage API returned a non-object response")
    return value


def fetch_admin_events(
    key: str, email: str, start_ms: int, end_ms: int, url: str = DEFAULT_ADMIN_URL
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    page = 1
    while True:
        response = api_request(
            url,
            key,
            body={
                "startDate": start_ms,
                "endDate": end_ms,
                "email": email,
                "page": page,
                "pageSize": 1000,
            },
        )
        values = response.get("usageEvents", [])
        if isinstance(values, list):
            events.extend(item for item in values if isinstance(item, dict))
        pagination = response.get("pagination")
        if not isinstance(pagination, dict) or not pagination.get("hasNextPage"):
            break
        page += 1
    return events


def load_sync_state(workspace: Path) -> dict[str, Any]:
    path = workspace / SYNC_STATE
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def merge_sync_state(workspace: Path, updates: dict[str, Any]) -> None:
    """Merge into the shared sync-state file so the Admin-API and Cloud-Agent
    sync paths can each persist their own watermarks without clobbering the
    other's (they share one file under `.adlc5/cursor-usage-sync.json`)."""
    state = load_sync_state(workspace)
    state.update(updates)
    write_json(workspace / SYNC_STATE, state)


def sync_workspace(
    workspace: Path, config: dict[str, str], *, force: bool = False
) -> dict[str, Any]:
    bindings = discover_bindings(workspace)
    if not bindings:
        return {"status": "skipped", "reason": "no-bindings", "recorded": 0}

    key = config.get("CURSOR_ADMIN_API_KEY", "")
    email = config.get("CURSOR_USAGE_EMAIL", "")
    if not key or not email:
        raise ValueError(
            "CURSOR_ADMIN_API_KEY and CURSOR_USAGE_EMAIL are required in "
            f"{DEFAULT_CONFIG}"
        )

    current_ms = now_ms()
    state = load_sync_state(workspace)
    last_sync_ms = int(state.get("last_sync_ms", 0) or 0)
    if not force and current_ms - last_sync_ms < MIN_SYNC_INTERVAL_MS:
        return {"status": "skipped", "reason": "rate-limit", "recorded": 0}

    earliest_ms = min(parse_int(item.get("bound_at_ms")) or current_ms for item in bindings)
    start_ms = earliest_ms
    if last_sync_ms:
        start_ms = max(earliest_ms, last_sync_ms - SYNC_OVERLAP_MS)
    url = config.get("CURSOR_ADMIN_API_URL", DEFAULT_ADMIN_URL)
    events = fetch_admin_events(key, email, start_ms, current_ms, url)
    result = ingest_events(workspace, events)
    merge_sync_state(
        workspace,
        {
            "last_sync_ms": current_ms,
            "window_start_ms": start_ms,
            "events_received": len(events),
        },
    )
    return {"status": "ok", "events_received": len(events), **result}


def usage_delta(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, int]:
    """Cloud Agent usage is cumulative per run while it is still executing.
    Return only the newly-observed tokens since the last poll, clamped at
    zero so a stale/reset counter never yields a negative delta."""
    previous = previous or {}
    return {
        field: max(0, int(current.get(field, 0) or 0) - int(previous.get(field, 0) or 0))
        for field in CLOUD_USAGE_FIELDS
    }


def has_positive_usage(delta: dict[str, int]) -> bool:
    return any(value > 0 for value in delta.values())


def discover_cloud_agents(
    key: str, url: str = DEFAULT_CLOUD_URL, *, limit: int = 100
) -> list[dict[str, Any]]:
    agents: list[dict[str, Any]] = []
    cursor_token: str | None = None
    while True:
        query: dict[str, Any] = {"limit": limit}
        if cursor_token:
            query["cursor"] = cursor_token
        response = api_request(f"{url}?{urllib.parse.urlencode(query)}", key)
        items = response.get("items", [])
        if isinstance(items, list):
            agents.extend(item for item in items if isinstance(item, dict))
        next_cursor = response.get("nextCursor")
        if not next_cursor:
            break
        cursor_token = str(next_cursor)
    return agents


def fetch_agent_usage(key: str, agent_id: str, url: str = DEFAULT_CLOUD_URL) -> dict[str, Any]:
    response = api_request(f"{url}/{urllib.parse.quote(agent_id)}/usage", key)
    runs = response.get("runs")
    return response if isinstance(runs, list) else {"runs": []}


def record_cloud_delta(
    workspace: Path,
    binding: dict[str, Any],
    agent_id: str,
    run_id: str,
    delta: dict[str, int],
    usage_after: dict[str, Any],
) -> None:
    fingerprint = hashlib.sha256(
        json.dumps(
            {"agent_id": agent_id, "run_id": run_id, "usage_after": usage_after},
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    extra = {
        "cursor_usage_event_id": fingerprint,
        "cloud_agent_id": agent_id,
        "cloud_run_id": run_id,
    }
    common.record_usage(
        workspace=workspace,
        feature=str(binding["feature"]),
        model_id=str(binding.get("model_id") or "unknown"),
        platform=CLOUD_PLATFORM,
        source="api",
        input_tokens=delta["inputTokens"],
        output_tokens=delta["outputTokens"],
        cache_creation_tokens=delta["cacheWriteTokens"],
        cache_read_tokens=delta["cacheReadTokens"],
        total_tokens=delta["totalTokens"],
        run_id=run_id,
        stage=binding.get("stage"),
        step=binding.get("step"),
        extra=extra,
    )


def latest_cloud_bindings(workspace: Path) -> dict[str, dict[str, Any]]:
    """Cloud Agent IDs (`bc-...`) are bound the same way as IDE conversation
    IDs, via `cursor-usage.py bind --conversation-id bc-...`. Keep only the
    most recent binding per agent."""
    by_agent: dict[str, dict[str, Any]] = {}
    for binding in discover_bindings(workspace):
        agent_id = binding.get("conversation_id")
        if not agent_id or not str(agent_id).startswith("bc-"):
            continue
        agent_id = str(agent_id)
        existing = by_agent.get(agent_id)
        new_bound_ms = parse_int(binding.get("bound_at_ms", 0)) or 0
        old_bound_ms = parse_int(existing.get("bound_at_ms", 0)) or 0 if existing else -1
        if not existing or new_bound_ms >= old_bound_ms:
            by_agent[agent_id] = binding
    return by_agent


def sync_cloud_workspace(
    workspace: Path, config: dict[str, str], *, force: bool = False
) -> dict[str, Any]:
    agent_bindings = latest_cloud_bindings(workspace)
    if not agent_bindings:
        return {"status": "skipped", "reason": "no-cloud-bindings", "recorded": 0}

    key = config.get("CURSOR_API_KEY") or config.get("CURSOR_ADMIN_API_KEY", "")
    if not key:
        raise ValueError(f"CURSOR_API_KEY or CURSOR_ADMIN_API_KEY is required in {DEFAULT_CONFIG}")

    current_ms = now_ms()
    state = load_sync_state(workspace)
    last_sync_ms = int(state.get("last_cloud_sync_ms", 0) or 0)
    if not force and current_ms - last_sync_ms < MIN_SYNC_INTERVAL_MS:
        return {"status": "skipped", "reason": "rate-limit", "recorded": 0}

    url = config.get("CURSOR_CLOUD_API_URL", DEFAULT_CLOUD_URL)
    run_watermarks: dict[str, Any] = dict(state.get("cloud_runs") or {})
    recorded = 0
    errors: list[str] = []
    for agent_id, binding in agent_bindings.items():
        try:
            usage_response = fetch_agent_usage(key, agent_id, url)
        except RuntimeError as error:
            errors.append(f"{agent_id}: {error}")
            continue
        for run in usage_response.get("runs", []):
            if not isinstance(run, dict) or not isinstance(run.get("usage"), dict):
                continue
            run_id = str(run.get("id") or "")
            if not run_id:
                continue
            watermark_key = f"{agent_id}:{run_id}"
            delta = usage_delta(run_watermarks.get(watermark_key), run["usage"])
            if has_positive_usage(delta):
                record_cloud_delta(workspace, binding, agent_id, run_id, delta, run["usage"])
                recorded += 1
            run_watermarks[watermark_key] = run["usage"]

    merge_sync_state(
        workspace,
        {"last_cloud_sync_ms": current_ms, "cloud_runs": run_watermarks},
    )
    result: dict[str, Any] = {"status": "ok", "recorded": recorded}
    if errors:
        result["errors"] = errors
    return result


def hook_workspaces(payload: dict[str, Any]) -> list[Path]:
    roots = payload.get("workspace_roots")
    if isinstance(roots, list):
        return [Path(root) for root in roots if isinstance(root, str)]
    project = os.environ.get("CURSOR_PROJECT_DIR")
    return [Path(project)] if project else [Path.cwd()]


def cmd_hook(args: argparse.Namespace) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    feature = extract_feature(payload)
    conversation_id = payload.get("conversation_id") or payload.get("session_id")
    for workspace in hook_workspaces(payload):
        if (workspace / ".adlc5").is_dir():
            register_workspace(workspace)
            if feature and conversation_id:
                bind_usage(
                    workspace,
                    feature,
                    str(conversation_id),
                    model_id=str(payload.get("model_id") or payload.get("model") or "") or None,
                )
    if args.event == "pre-tool":
        print('{"permission":"allow"}')
    elif args.event == "before-submit":
        print('{"continue":true}')
    elif args.event == "session-start":
        session_id = payload.get("session_id")
        print(json.dumps({"env": {"ADLC5_CURSOR_SESSION_ID": str(session_id or "")}}))
    return 0


def cmd_bind(args: argparse.Namespace) -> int:
    conversation_id = args.conversation_id or os.environ.get("ADLC5_CURSOR_SESSION_ID")
    if not conversation_id:
        raise ValueError("--conversation-id is required outside a Cursor session")
    binding = bind_usage(Path(args.workspace), args.feature, conversation_id)
    print(json.dumps({"status": "ok", "binding": binding}, indent=2))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    config = read_config(Path(args.config).expanduser())
    result = sync_workspace(Path(args.workspace).resolve(), config, force=args.force)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_sync_all(args: argparse.Namespace) -> int:
    config = read_config(Path(args.config).expanduser())
    results: dict[str, Any] = {}
    for workspace in registered_workspaces():
        try:
            results[str(workspace)] = sync_workspace(workspace, config, force=args.force)
        except Exception as error:
            results[str(workspace)] = {"status": "error", "error": str(error)}
    print(json.dumps({"status": "ok", "workspaces": results}, indent=2, sort_keys=True))
    return 0


def cmd_sync_cloud(args: argparse.Namespace) -> int:
    config = read_config(Path(args.config).expanduser())
    result = sync_cloud_workspace(Path(args.workspace).resolve(), config, force=args.force)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_sync_cloud_all(args: argparse.Namespace) -> int:
    config = read_config(Path(args.config).expanduser())
    results: dict[str, Any] = {}
    for workspace in registered_workspaces():
        try:
            results[str(workspace)] = sync_cloud_workspace(workspace, config, force=args.force)
        except Exception as error:
            results[str(workspace)] = {"status": "error", "error": str(error)}
    print(json.dumps({"status": "ok", "workspaces": results}, indent=2, sort_keys=True))
    return 0


def cmd_cloud(args: argparse.Namespace) -> int:
    config = read_config(Path(args.config).expanduser())
    key = config.get("CURSOR_API_KEY") or config.get("CURSOR_ADMIN_API_KEY")
    if not key:
        raise ValueError("CURSOR_API_KEY or CURSOR_ADMIN_API_KEY is required")
    query = urllib.parse.urlencode({"runId": args.run_id}) if args.run_id else ""
    base = config.get("CURSOR_CLOUD_API_URL", DEFAULT_CLOUD_URL).rstrip("/")
    url = f"{base}/{urllib.parse.quote(args.agent_id)}/usage"
    if query:
        url = f"{url}?{query}"
    response = api_request(url, key)
    workspace = Path(args.workspace).resolve()
    known = ledger_event_ids(workspace)
    recorded = 0
    for run in response.get("runs", []):
        if not isinstance(run, dict) or not isinstance(run.get("usage"), dict):
            continue
        fingerprint = hashlib.sha256(
            f"cloud:{args.agent_id}:{run.get('id')}".encode("utf-8")
        ).hexdigest()
        if fingerprint in known:
            continue
        usage = run["usage"]
        extra = {
            "cursor_usage_event_id": fingerprint,
            "cloud_agent_id": args.agent_id,
            "usage_uuid": run.get("usageUuid"),
        }
        common.record_usage(
            workspace=workspace,
            feature=args.feature,
            model_id=args.model_id,
            platform=CLOUD_PLATFORM,
            source="api",
            input_tokens=int(usage.get("inputTokens", 0) or 0),
            output_tokens=int(usage.get("outputTokens", 0) or 0),
            cache_creation_tokens=int(usage.get("cacheWriteTokens", 0) or 0),
            cache_read_tokens=int(usage.get("cacheReadTokens", 0) or 0),
            total_tokens=int(usage.get("totalTokens", 0) or 0),
            run_id=str(run.get("id") or ""),
            extra=extra,
        )
        known.add(fingerprint)
        recorded += 1
    print(json.dumps({"status": "ok", "recorded": recorded}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    hook = subparsers.add_parser("hook")
    hook.add_argument("event", choices=["before-submit", "pre-tool", "session-start", "session-end"])
    hook.set_defaults(func=cmd_hook)

    bind = subparsers.add_parser("bind")
    bind.add_argument("--feature", required=True)
    bind.add_argument("--workspace", default=".")
    bind.add_argument("--conversation-id")
    bind.set_defaults(func=cmd_bind)

    sync = subparsers.add_parser("sync")
    sync.add_argument("--workspace", default=".")
    sync.add_argument("--config", default=str(DEFAULT_CONFIG))
    sync.add_argument("--force", action="store_true")
    sync.set_defaults(func=cmd_sync)

    sync_all = subparsers.add_parser("sync-all")
    sync_all.add_argument("--config", default=str(DEFAULT_CONFIG))
    sync_all.add_argument("--force", action="store_true")
    sync_all.set_defaults(func=cmd_sync_all)

    sync_cloud = subparsers.add_parser("sync-cloud")
    sync_cloud.add_argument("--workspace", default=".")
    sync_cloud.add_argument("--config", default=str(DEFAULT_CONFIG))
    sync_cloud.add_argument("--force", action="store_true")
    sync_cloud.set_defaults(func=cmd_sync_cloud)

    sync_cloud_all = subparsers.add_parser("sync-cloud-all")
    sync_cloud_all.add_argument("--config", default=str(DEFAULT_CONFIG))
    sync_cloud_all.add_argument("--force", action="store_true")
    sync_cloud_all.set_defaults(func=cmd_sync_cloud_all)

    cloud = subparsers.add_parser("cloud")
    cloud.add_argument("--feature", required=True)
    cloud.add_argument("--agent-id", required=True)
    cloud.add_argument("--run-id")
    cloud.add_argument("--model-id", required=True)
    cloud.add_argument("--workspace", default=".")
    cloud.add_argument("--config", default=str(DEFAULT_CONFIG))
    cloud.set_defaults(func=cmd_cloud)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
