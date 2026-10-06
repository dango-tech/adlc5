"""Shared plumbing for per-platform ADLC5 agent usage collectors.

Each platform (cursor, claude, codex, ...) owns its own hook-payload and
transcript/rollout parsing -- that part is genuinely platform-specific and
lives in scripts/{platform}-usage.py. This module holds the parts that are
identical across platforms:

- ADLC5 feature/stage/step binding (conversation/session id -> feature)
- Deduplicated recording into the shared usage-ledger.jsonl sink

See docs/agent-usage.md for the per-platform capability matrix.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
LEDGER = ROOT / "scripts" / "memory" / "usage-ledger.py"

# Dedup fingerprints are stored under one of these keys in a ledger entry's
# `extra` object, depending on which collector wrote it. Checked together so
# any collector's ledger_event_ids() call sees every platform's history.
LEDGER_EVENT_ID_KEYS = ("usage_event_id", "cursor_usage_event_id")

FEATURE_PATTERN = re.compile(
    r"@adlc5(?:-(?:specify|plan|tasks|implement))?\s+(?:for\s+)?"
    r"([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)",
    re.IGNORECASE,
)
FEATURE_ARG_PATTERN = re.compile(r"(?:^|\s)--feature(?:=|\s+)([a-z0-9][a-z0-9-]*)")


def now_ms() -> int:
    return int(time.time() * 1000)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            entries.append(value)
    return entries


def load_state(feature_dir: Path) -> dict[str, Any]:
    path = feature_dir / "state.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_feature(value: Any) -> str | None:
    if isinstance(value, str):
        match = FEATURE_PATTERN.search(value) or FEATURE_ARG_PATTERN.search(value)
        return match.group(1) if match else None
    if isinstance(value, dict):
        for nested in value.values():
            feature = extract_feature(nested)
            if feature:
                return feature
    if isinstance(value, list):
        for nested in value:
            feature = extract_feature(nested)
            if feature:
                return feature
    return None


def registry_path(platform: str) -> Path:
    return Path.home() / ".adlc5" / f"{platform}-usage-workspaces.json"


def bindings_relpath(platform: str) -> Path:
    return Path(".adlc5") / f"{platform}-usage-bindings.jsonl"


def register_workspace(platform: str, workspace: Path) -> None:
    workspace = workspace.resolve()
    registry = registry_path(platform)
    values: list[str] = []
    if registry.is_file():
        try:
            existing = json.loads(registry.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                values = [str(Path(item).resolve()) for item in existing if isinstance(item, str)]
        except json.JSONDecodeError:
            pass
    resolved = str(workspace)
    if resolved not in values:
        values.append(resolved)
        write_json(registry, sorted(set(values)))


def registered_workspaces(platform: str) -> list[Path]:
    registry = registry_path(platform)
    if not registry.is_file():
        return []
    try:
        values = json.loads(registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(values, list):
        return []
    return [Path(value) for value in values if isinstance(value, str) and Path(value).is_dir()]


def bind_usage(
    platform: str,
    workspace: Path,
    feature: str,
    conversation_id: str,
    *,
    model_id: str | None = None,
    bound_at_ms: int | None = None,
) -> dict[str, Any]:
    feature_dir = workspace / ".adlc5" / feature
    state = load_state(feature_dir)
    binding = {
        "conversation_id": conversation_id,
        "feature": feature,
        "stage": state.get("current_stage"),
        "step": state.get("current_step"),
        "model_id": model_id,
        "bound_at_ms": bound_at_ms if bound_at_ms is not None else now_ms(),
    }
    path = workspace / bindings_relpath(platform)
    existing = load_jsonl(path)
    if existing:
        comparable = {key: value for key, value in binding.items() if key != "bound_at_ms"}
        latest = {key: value for key, value in existing[-1].items() if key != "bound_at_ms"}
        if comparable == latest:
            return existing[-1]
    append_jsonl(path, binding)
    register_workspace(platform, workspace)
    return binding


def discover_bindings(platform: str, workspace: Path) -> list[dict[str, Any]]:
    bindings = load_jsonl(workspace / bindings_relpath(platform))
    adlc5_dir = workspace / ".adlc5"
    if adlc5_dir.is_dir():
        for feature_dir in adlc5_dir.iterdir():
            if feature_dir.is_dir():
                bindings.extend(
                    load_jsonl(feature_dir / "memory" / f"{platform}-usage-bindings.jsonl")
                )
    return bindings


def select_binding(
    bindings: list[dict[str, Any]], event_timestamp_ms: int
) -> dict[str, Any] | None:
    eligible: list[tuple[int, dict[str, Any]]] = []
    for binding in bindings:
        bound_at_ms = parse_int(binding.get("bound_at_ms", 0))
        if bound_at_ms is not None and bound_at_ms <= event_timestamp_ms:
            eligible.append((bound_at_ms, binding))
    return max(eligible, key=lambda item: item[0])[1] if eligible else None


def usage_ledger_paths(workspace: Path) -> list[Path]:
    adlc5_dir = workspace / ".adlc5"
    if not adlc5_dir.is_dir():
        return []
    ledgers = list(adlc5_dir.glob("*/memory/usage-ledger.jsonl"))
    archive_dir = adlc5_dir / "_archive"
    if archive_dir.is_dir():
        ledgers.extend(archive_dir.glob("*/memory/usage-ledger.jsonl"))
    return ledgers


def ledger_event_ids(workspace: Path) -> set[str]:
    ids: set[str] = set()
    for ledger in usage_ledger_paths(workspace):
        for entry in load_jsonl(ledger):
            extra = entry.get("extra")
            if not isinstance(extra, dict):
                continue
            for key in LEDGER_EVENT_ID_KEYS:
                if extra.get(key):
                    ids.add(str(extra[key]))
    return ids


def record_usage(
    *,
    workspace: Path,
    feature: str,
    model_id: str,
    platform: str,
    source: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    total_tokens: int | None = None,
    run_id: str = "",
    stage: str | None = None,
    step: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    command = [
        sys.executable,
        str(LEDGER),
        "record",
        "--feature",
        feature,
        "--workspace",
        str(workspace),
        "--model-id",
        model_id,
        "--platform",
        platform,
        "--source",
        source,
        "--input-tokens",
        str(int(input_tokens)),
        "--output-tokens",
        str(int(output_tokens)),
        "--cache-creation-tokens",
        str(int(cache_creation_tokens)),
        "--cache-read-tokens",
        str(int(cache_read_tokens)),
    ]
    if total_tokens is not None:
        command.extend(["--total-tokens", str(int(total_tokens))])
    if run_id:
        command.extend(["--run-id", run_id])
    if stage:
        command.extend(["--stage", str(stage)])
    if step:
        command.extend(["--step", str(step)])
    if extra:
        command.extend(["--extra-json", json.dumps(extra, separators=(",", ":"))])
    subprocess.run(command, check=True, capture_output=True, text=True)
