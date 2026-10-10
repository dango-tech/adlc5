"""Host command construction and usage normalization for unattended ADLC5 runs."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def command(*, workspace: Path, prompt: str, model: str | None, effort: str | None) -> list[str]:
    """Build a Codex CLI invocation with writes confined to the workspace."""
    argv = ["codex", "exec", "--json", "--color", "never", "--sandbox", "workspace-write", "--approve-for-me",
            "--ignore-user-config", "--ignore-rules", "-C", str(workspace)]
    if model and model.lower() not in ("inherit", "host default"):
        argv.extend(("-m", model))
    if effort:
        argv.extend(("-c", f"model_reasoning_effort={effort}"))
    argv.append(prompt)
    return argv


def parse_events(text: str) -> dict[str, Any]:
    """Return final assistant text and the last turn's available token usage."""
    final = ""
    usage: dict[str, int] = {}
    model = None
    session_id = None
    calls = 0
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") in ("thread.started", "thread.resumed"):
            session_id = event.get("thread_id") or session_id
        if event.get("type") == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                final = item["text"]
        if event.get("type") == "turn.completed":
            calls += 1
            turn_usage = event.get("usage") or {}
            details = turn_usage.get("output_tokens_details") or {}
            normalized = {
                "input": turn_usage.get("input_tokens"),
                "cache_read": turn_usage.get("cached_input_tokens"),
                "cache_creation": turn_usage.get("cache_write_input_tokens"),
                "output": turn_usage.get("output_tokens"),
                "thinking": turn_usage.get("reasoning_output_tokens") or details.get("reasoning_tokens"),
            }
            for target, value in normalized.items():
                if type(value) is int and value >= 0:
                    usage[target] = value
            model = (event.get("model_provider") or {}).get("model") or event.get("model") or model
        if event.get("type") == "token_usage_record":
            reported = event.get("payload", {}).get("turn_token_usage") or event.get("payload", {}).get("usage") or event.get("usage") or {}
            normalized = {"input": "input_tokens", "cache_read": "cached_input_tokens",
                          "cache_creation": "cache_write_input_tokens", "output": "output_tokens",
                          "thinking": "reasoning_output_tokens"}
            for target, source in normalized.items():
                value = reported.get(source)
                if type(value) is int and value >= 0:
                    usage[target] = value
            session_id = event.get("payload", {}).get("session_id") or session_id
    return {"text": final, "usage": usage, "model_id": model, "session_id": session_id, "calls": calls}


def resolve_model(root: Path, workspace: Path, feature: str, tier: str) -> dict[str, Any]:
    import subprocess

    proc = subprocess.run([str(root / "scripts/resolve-model.sh"), "--platform", "codex", "--tier", tier,
                           "--workspace", str(workspace), "--feature", feature],
                          cwd=workspace, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "model resolution failed")
    result = json.loads(proc.stdout)
    if not isinstance(result, dict) or result.get("error"):
        raise RuntimeError(str(result.get("error", "invalid model resolution")))
    return result


def environment() -> dict[str, str]:
    return {**os.environ, "ADLC5_PLATFORM": "codex"}
