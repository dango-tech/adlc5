#!/usr/bin/env python3
"""Collect official Claude Code token usage into ADLC5 feature ledgers.

Claude Code hook payloads carry no usage/model fields directly (unlike
Cursor's, which include `model`/`model_id` on every hook). What every hook
does carry is `transcript_path`, and the transcript JSONL Claude Code writes
to disk already contains `message.model` and `message.usage` for each
completed assistant turn -- the exact provider-reported token counts, not an
estimate, and no API key or network call needed. See docs/claude-usage.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import agent_usage_common as common  # noqa: E402

PLATFORM = "claude"

now_ms = common.now_ms
parse_int = common.parse_int
extract_feature = common.extract_feature
ledger_event_ids = common.ledger_event_ids


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


def parse_transcript_timestamp(value: Any) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return int(datetime.fromisoformat(text).timestamp() * 1000)
    except ValueError:
        return None


def iter_assistant_turns(transcript_path: Path) -> list[dict[str, Any]]:
    """Each completed assistant turn Claude Code appends to the transcript
    carries its own `message.model` and `message.usage` -- the exact
    per-turn token counts Anthropic's API returned for that turn."""
    if not transcript_path.is_file():
        return []
    turns: list[dict[str, Any]] = []
    for line in transcript_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "assistant":
            continue
        message = entry.get("message")
        if isinstance(message, dict) and isinstance(message.get("usage"), dict):
            turns.append(entry)
    return turns


def turn_fingerprint(session_id: str, entry: dict[str, Any]) -> str:
    message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
    key = entry.get("uuid") or entry.get("requestId") or json.dumps(
        message.get("usage"), sort_keys=True
    )
    return hashlib.sha256(f"{session_id}:{key}".encode("utf-8")).hexdigest()


def record_turn(
    workspace: Path,
    binding: dict[str, Any],
    session_id: str,
    entry: dict[str, Any],
    fingerprint: str,
    event_timestamp_ms: int,
) -> None:
    message = entry["message"]
    usage = message["usage"]
    extra = {
        "usage_event_id": fingerprint,
        "conversation_id": session_id,
        "event_timestamp_ms": event_timestamp_ms,
    }
    common.record_usage(
        workspace=workspace,
        feature=str(binding["feature"]),
        model_id=str(message.get("model") or binding.get("model_id") or "unknown"),
        platform=PLATFORM,
        source="transcript",
        input_tokens=int(usage.get("input_tokens", 0) or 0),
        output_tokens=int(usage.get("output_tokens", 0) or 0),
        cache_creation_tokens=int(usage.get("cache_creation_input_tokens", 0) or 0),
        cache_read_tokens=int(usage.get("cache_read_input_tokens", 0) or 0),
        run_id=session_id,
        stage=binding.get("stage"),
        step=binding.get("step"),
        extra=extra,
    )


def ingest_transcript(workspace: Path, session_id: str, transcript_path: Path) -> dict[str, int]:
    session_bindings = [
        binding
        for binding in discover_bindings(workspace)
        if str(binding.get("conversation_id")) == session_id
    ]
    if not session_bindings:
        return {"recorded": 0, "skipped": 0}

    known = ledger_event_ids(workspace)
    recorded = skipped = 0
    for entry in iter_assistant_turns(transcript_path):
        fingerprint = turn_fingerprint(session_id, entry)
        if fingerprint in known:
            skipped += 1
            continue
        event_timestamp_ms = parse_transcript_timestamp(entry.get("timestamp")) or now_ms()
        binding = common.select_binding(session_bindings, event_timestamp_ms)
        if not binding:
            skipped += 1
            continue
        record_turn(workspace, binding, session_id, entry, fingerprint, event_timestamp_ms)
        known.add(fingerprint)
        recorded += 1
    return {"recorded": recorded, "skipped": skipped}


def hook_workspace(payload: dict[str, Any]) -> Path:
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        return Path(cwd)
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(project) if project else Path.cwd()


def cmd_hook(args: argparse.Namespace) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    workspace = hook_workspace(payload)
    session_id = payload.get("session_id")
    if not (workspace / ".adlc5").is_dir() or not session_id:
        return 0

    if args.event == "user-prompt-submit":
        feature = extract_feature(payload.get("prompt"))
        if feature:
            bind_usage(workspace, feature, str(session_id))
    elif args.event == "stop":
        transcript_path = payload.get("transcript_path")
        if transcript_path:
            ingest_transcript(workspace, str(session_id), Path(transcript_path))
    return 0


def cmd_bind(args: argparse.Namespace) -> int:
    binding = bind_usage(Path(args.workspace), args.feature, args.session_id)
    print(json.dumps({"status": "ok", "binding": binding}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    hook = subparsers.add_parser("hook")
    hook.add_argument("event", choices=["user-prompt-submit", "stop"])
    hook.set_defaults(func=cmd_hook)

    bind = subparsers.add_parser("bind")
    bind.add_argument("--feature", required=True)
    bind.add_argument("--workspace", default=".")
    bind.add_argument("--session-id", required=True)
    bind.set_defaults(func=cmd_bind)

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
