#!/usr/bin/env python3
"""Preview and explicitly share minimized ADLC5 telemetry."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

EVENT_BUCKETS = ("script_start", "script_end", "checkpoint", "gate_fail", "stage_picker", "phase_advance", "policy_decision", "other")
STATUS_BUCKETS = ("pass", "fail", "blocked", "warn", "other")
EVENT_MAP = {key: key for key in EVENT_BUCKETS if key != "other"}
EVENT_MAP.update({"script.start": "script_start", "script.end": "script_end"})
STATUS_MAP = {key: key for key in STATUS_BUCKETS if key != "other"}
MAX_EVENT_FILE = 10 * 1024 * 1024
MAX_QUEUE = 10


def telemetry_dir(workspace: Path) -> Path:
    return workspace / ".adlc5" / "telemetry"


def consent_path(workspace: Path) -> Path:
    return telemetry_dir(workspace) / "sharing-consent.json"


def outbox_path(workspace: Path) -> Path:
    return telemetry_dir(workspace) / "outbox.jsonl"


def cursor_path(workspace: Path) -> Path:
    return telemetry_dir(workspace) / "sharing-cursor.json"


def is_enabled(workspace: Path) -> bool:
    try:
        record = json.loads(consent_path(workspace).read_text(encoding="utf-8"))
        return record == {"schema_version": 1, "enabled": True}
    except (OSError, ValueError, TypeError):
        return False


def set_enabled(workspace: Path, enabled: bool) -> None:
    path = consent_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not enabled:
        path.unlink(missing_ok=True)
        outbox_path(workspace).unlink(missing_ok=True)
        cursor_path(workspace).unlink(missing_ok=True)
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schema_version": 1, "enabled": True}) + "\n", encoding="utf-8")
    tmp.replace(path)


def prepare_aggregate(workspace: Path) -> tuple[dict[str, Any], dict[str, int]]:
    events = Counter({key: 0 for key in EVENT_BUCKETS})
    statuses = Counter({key: 0 for key in STATUS_BUCKETS})
    root = workspace / ".adlc5"
    try:
        previous = json.loads(cursor_path(workspace).read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            previous = {}
    except (OSError, ValueError):
        previous = {}
    cursor: dict[str, int] = {}
    for path in sorted(root.glob("*/telemetry/events.jsonl")):
        if path.stat().st_size > MAX_EVENT_FILE:
            raise ValueError(f"local event file exceeds {MAX_EVENT_FILE} bytes: {path}")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        key = path.relative_to(root).as_posix()
        offset = previous.get(key, 0)
        if not isinstance(offset, int) or offset < 0 or offset > len(lines):
            offset = 0
        cursor[key] = len(lines)
        for line in lines[offset:]:
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(record, dict):
                continue
            event_name, status_name = record.get("event"), record.get("status")
            event = EVENT_MAP.get(event_name, "other") if isinstance(event_name, str) else "other"
            status = STATUS_MAP.get(status_name, "other") if isinstance(status_name, str) else "other"
            events[event] = min(events[event] + 1, 1_000_000)
            statuses[status] = min(statuses[status] + 1, 1_000_000)
    return ({
        "schema_version": 1,
        "kind": "aggregate",
        "events": dict(events),
        "statuses": dict(statuses),
    }, cursor)


def aggregate(workspace: Path) -> dict[str, Any]:
    return prepare_aggregate(workspace)[0]


def _queue_records(workspace: Path) -> list[dict[str, Any]]:
    path = outbox_path(workspace)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if not isinstance(item, dict) or set(item) != {"submission_id", "payload", "cursor"}:
            raise ValueError("invalid telemetry outbox; refusing to send")
        records.append(item)
    return records


def _write_queue(workspace: Path, records: list[dict[str, Any]]) -> None:
    path = outbox_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(item, separators=(",", ":")) + "\n" for item in records), encoding="utf-8")
    tmp.replace(path)


def _write_cursor(workspace: Path, cursor: dict[str, int]) -> None:
    path = cursor_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cursor, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(path)


def enqueue(workspace: Path, payload: dict[str, Any], cursor: dict[str, int]) -> None:
    records = _queue_records(workspace)
    if len(records) >= MAX_QUEUE:
        raise ValueError(f"telemetry outbox is full ({MAX_QUEUE}); send or opt out to clear it")
    records.append({"submission_id": str(uuid.uuid4()), "payload": payload, "cursor": cursor})
    _write_queue(workspace, records)


def post_payload(endpoint: str, route: str, payload: dict[str, Any], submission_id: str | None = None) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode()
    if len(body) > 4096:
        raise ValueError("payload exceeds 4096 bytes")
    headers = {"Content-Type": "application/json"}
    if submission_id:
        headers["Idempotency-Key"] = submission_id
    request = urllib.request.Request(endpoint.rstrip("/") + route, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status not in (200, 201, 202):
            raise OSError(f"telemetry endpoint returned HTTP {response.status}")


def send_aggregate(workspace: Path, endpoint: str, retries: int = 2) -> int:
    if not is_enabled(workspace):
        print("Telemetry sharing is off. Preview first, then explicitly opt in.", file=sys.stderr)
        return 2
    records = _queue_records(workspace)
    if not records:
        payload, cursor = prepare_aggregate(workspace)
        enqueue(workspace, payload, cursor)
        records = _queue_records(workspace)
    item = records[0]
    for attempt in range(retries):
        try:
            post_payload(endpoint, "/v1/aggregate", item["payload"], item["submission_id"])
            _write_cursor(workspace, item["cursor"])
            _write_queue(workspace, records[1:])
            print("Aggregate sent; local queue updated.")
            return 0
        except (OSError, ValueError, urllib.error.URLError) as exc:
            if attempt + 1 < retries:
                time.sleep(0.25)
            else:
                print(f"Send failed after {retries} attempts; queued payload retained: {exc}", file=sys.stderr)
    return 1


def feedback_payload(rating: int, category: str, text: str = "") -> dict[str, Any]:
    if rating not in range(1, 6) or category not in ("bug", "idea", "positive", "other"):
        raise ValueError("rating must be 1-5 and category must be bug|idea|positive|other")
    if len(text) > 1000:
        raise ValueError("feedback text is limited to 1000 characters")
    return {"schema_version": 1, "kind": "feedback", "rating": rating, "category": category, **({"text": text} if text else {})}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "opt-in", "opt-out", "send", "feedback"))
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--endpoint", default=os.environ.get("ADLC5_TELEMETRY_ENDPOINT", ""))
    parser.add_argument("--rating", type=int)
    parser.add_argument("--category", choices=("bug", "idea", "positive", "other"))
    parser.add_argument("--text", default="")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    try:
        if args.action == "preview":
            print(json.dumps(aggregate(workspace), indent=2))
            print("Sharing is " + ("enabled" if is_enabled(workspace) else "off") + ". No network request was made.")
            return 0
        if args.action == "opt-in":
            print("Preview of the only telemetry fields ADLC5 may send:")
            print(json.dumps(aggregate(workspace), indent=2))
            print("No prompts, code, commands, output, repository/feature labels, dates, or user ID are included.")
            print("Sending is always manual via `adlc5 telemetry send`; Cloudflare still processes connection metadata.")
            if input("Enable local opt-in for this workspace? Type yes: ").strip().lower() != "yes":
                print("No change; telemetry sharing remains off.")
                return 0
            set_enabled(workspace, True)
            print("Opted in. Nothing has been sent.")
            return 0
        if args.action == "opt-out":
            set_enabled(workspace, False)
            print("Opted out; local queued telemetry deleted. Data already submitted cannot be recalled here.")
            return 0
        if args.action == "send":
            if not args.endpoint.startswith("https://"):
                raise ValueError("set ADLC5_TELEMETRY_ENDPOINT to your HTTPS intake URL")
            print(json.dumps(aggregate(workspace), indent=2))
            if input("Send this minimized aggregate now? Type yes: ").strip().lower() != "yes":
                print("Not sent.")
                return 0
            return send_aggregate(workspace, args.endpoint)
        if args.action == "feedback":
            if not args.endpoint.startswith("https://"):
                raise ValueError("set ADLC5_TELEMETRY_ENDPOINT to your HTTPS intake URL")
            rating = args.rating if args.rating is not None else int(input("Rating (1-5): "))
            category = args.category or input("Category (bug|idea|positive|other): ").strip()
            include_text = args.text
            if not include_text and input("Include optional free-text feedback? (y/N): ").strip().lower() == "y":
                include_text = input("Feedback (max 1000 characters; avoid secrets or personal data): ")
            payload = feedback_payload(rating, category, include_text)
            print(json.dumps(payload, indent=2))
            print("Free text is stored separately from aggregate telemetry and is not anonymous.")
            if input("Submit this feedback now? Type yes: ").strip().lower() != "yes":
                print("Not submitted.")
                return 0
            post_payload(args.endpoint, "/v1/feedback", payload)
            print("Feedback submitted.")
            return 0
    except (ValueError, OSError, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
