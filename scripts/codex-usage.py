#!/usr/bin/env python3
"""Collect official Codex CLI token usage into ADLC5 feature ledgers.

Codex CLI's hooks engine (`.codex/hooks.json`) puts `model` directly on the
Stop/SubagentStop hook payload, same as Cursor. Token counts are not in the
hook payload, but every hook also carries `transcript_path` -- the on-disk
rollout JSONL. Two real rollout item shapes carry token counts, checked in
this order (see docs/codex-usage.md for version notes):

1. `{"type": "token_usage_record", "payload": {turn_id, response_id, usage,
   ...}}` -- durably written per completed turn on some Codex CLI versions
   (codex-rs `RolloutItemWire::TokenUsageRecord`, structs
   `TokenUsageRecord`/`TokenUsage`). Matched by `turn_id` when present.
2. `{"type": "event_msg", "payload": {"type": "token_count", "info": {...}}}`
   -- observed directly on Codex CLI 0.144.0-alpha.4 rollouts when (1) is
   absent. Carries no turn_id/response_id, only a session-wide
   `info.last_token_usage` delta and `info.total_token_usage` running total;
   falls back to the most recent one in the file since Stop fires right
   after that turn's final update.

No API key or network call needed either way.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import agent_usage_common as common  # noqa: E402

PLATFORM = "codex"

now_ms = common.now_ms
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


def _find_token_usage_record_by_turn_id(lines: list[str], turn_id: str) -> dict[str, Any] | None:
    """Shape 1: a top-level `token_usage_record` rollout item matching this
    turn_id exactly. Reverse scan: the record for the turn that just
    finished is near the end of the file."""
    for line in reversed(lines):
        line = line.strip()
        if not line or '"token_usage_record"' not in line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "token_usage_record":
            continue
        payload = entry.get("payload")
        if isinstance(payload, dict) and str(payload.get("turn_id")) == turn_id:
            return payload
    return None


def _find_latest_token_count_info(lines: list[str]) -> dict[str, Any] | None:
    """Shape 2: the most recent `event_msg` rollout item whose inner payload
    is a `token_count` event. No turn_id/response_id exists in this shape at
    all -- only a session-wide `info.last_token_usage` delta and running
    `info.total_token_usage` total."""
    for line in reversed(lines):
        line = line.strip()
        if not line or '"token_count"' not in line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("type") != "event_msg":
            continue
        inner = entry.get("payload")
        if not isinstance(inner, dict) or inner.get("type") != "token_count":
            continue
        info = inner.get("info")
        if isinstance(info, dict):
            return info
    return None


def find_turn_usage(rollout_path: Path, turn_id: str) -> tuple[dict[str, Any], str] | None:
    """Returns (usage_fields, fingerprint_key) for the turn that just
    finished, trying the precise turn_id-matched shape first and falling
    back to the latest cumulative token_count update otherwise."""
    if not rollout_path.is_file():
        return None
    lines = rollout_path.read_text(encoding="utf-8", errors="replace").splitlines()

    record = _find_token_usage_record_by_turn_id(lines, turn_id)
    if record is not None:
        usage = record.get("usage") if isinstance(record.get("usage"), dict) else {}
        return usage, f"turn:{turn_id}:{record.get('response_id') or ''}"

    info = _find_latest_token_count_info(lines)
    if info is not None:
        last = info.get("last_token_usage") if isinstance(info.get("last_token_usage"), dict) else {}
        total = info.get("total_token_usage") if isinstance(info.get("total_token_usage"), dict) else {}
        # Cumulative total_tokens is monotonically increasing, so it uniquely
        # fingerprints "how far we've progressed" and dedupes correctly
        # across repeated Stop fires between real updates.
        return last, f"token_count:{total.get('total_tokens', '')}"

    return None


def record_fingerprint(session_id: str, fingerprint_key: str) -> str:
    return hashlib.sha256(f"{session_id}:{fingerprint_key}".encode("utf-8")).hexdigest()


def record_turn(
    workspace: Path,
    binding: dict[str, Any],
    session_id: str,
    turn_id: str,
    model: str,
    usage: dict[str, Any],
    fingerprint: str,
) -> None:
    extra = {
        "usage_event_id": fingerprint,
        "conversation_id": session_id,
        "turn_id": turn_id,
        "reasoning_output_tokens": int(usage.get("reasoning_output_tokens", 0) or 0),
    }
    common.record_usage(
        workspace=workspace,
        feature=str(binding["feature"]),
        model_id=model or str(binding.get("model_id") or "unknown"),
        platform=PLATFORM,
        source="transcript",
        input_tokens=int(usage.get("input_tokens", 0) or 0),
        output_tokens=int(usage.get("output_tokens", 0) or 0),
        cache_creation_tokens=int(usage.get("cache_write_input_tokens", 0) or 0),
        cache_read_tokens=int(usage.get("cached_input_tokens", 0) or 0),
        total_tokens=int(usage.get("total_tokens", 0) or 0),
        run_id=turn_id,
        stage=binding.get("stage"),
        step=binding.get("step"),
        extra=extra,
    )


def ingest_turn(
    workspace: Path, session_id: str, turn_id: str, model: str, transcript_path: Path
) -> dict[str, int]:
    session_bindings = [
        binding
        for binding in discover_bindings(workspace)
        if str(binding.get("conversation_id")) == session_id
    ]
    if not session_bindings:
        return {"recorded": 0, "skipped": 0}

    found = find_turn_usage(transcript_path, turn_id)
    if found is None:
        return {"recorded": 0, "skipped": 1}
    usage, fingerprint_key = found

    fingerprint = record_fingerprint(session_id, fingerprint_key)
    if fingerprint in ledger_event_ids(workspace):
        return {"recorded": 0, "skipped": 1}

    binding = common.select_binding(session_bindings, now_ms())
    if not binding:
        return {"recorded": 0, "skipped": 1}

    record_turn(workspace, binding, session_id, turn_id, model, usage, fingerprint)
    return {"recorded": 1, "skipped": 0}


def hook_workspace(payload: dict[str, Any]) -> Path:
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd:
        return Path(cwd)
    project = os.environ.get("CODEX_PROJECT_DIR")
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
            bind_usage(workspace, feature, str(session_id), model_id=payload.get("model"))
    elif args.event == "stop":
        transcript_path = payload.get("transcript_path")
        turn_id = payload.get("turn_id")
        if transcript_path and turn_id:
            ingest_turn(
                workspace,
                str(session_id),
                str(turn_id),
                str(payload.get("model") or ""),
                Path(transcript_path),
            )
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
