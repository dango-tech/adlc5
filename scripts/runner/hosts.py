"""Host command construction and usage normalization for supervised ADLC5 runs."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


HOSTS = ("codex", "claude", "cursor", "hermes")
MODES = {"codex": ("confined",), "claude": ("allowlist",), "cursor": ("confined",), "hermes": ("attended", "confined")}
AVAILABLE_MODES = {"codex": ("confined", "attended"), "claude": ("allowlist", "attended"),
                   "cursor": ("confined", "attended"), "hermes": ("attended", "confined")}


def in_declared_container(workspace: Path, runtime_detected: bool | None = None) -> bool:
    if runtime_detected is None:
        runtime_detected = Path("/.dockerenv").is_file() or Path("/run/.containerenv").is_file()
    if not runtime_detected:
        return False
    declaration = workspace / ".adlc5" / "external-sandbox.json"
    if not declaration.is_file():
        return False
    try:
        value = json.loads(declaration.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(value, dict) and value.get("type") == "container" and value.get("declared_by") == "user"


def command(*, host: str, mode: str, workspace: Path, prompt: str, model: str | None,
            effort: str | None, allowlist: list[str] | None = None, session_id: str | None = None,
            usage_file: Path | None = None, container_runtime_detected: bool | None = None) -> list[str]:
    """Build an invocation using only the host's declared supervision modes."""
    if host not in HOSTS:
        raise ValueError(f"unsupported host: {host}")
    if model and model.strip().lower() in ("inherit", "host default", "default"):
        model = None
    if host == "hermes" and mode != "attended" and not in_declared_container(workspace, container_runtime_detected):
        raise ValueError("unattended Hermes is refused outside a user-declared container")
    if mode not in MODES[host] and mode != "attended":
        raise ValueError(f"{host} does not support {mode} mode")
    if mode == "attended":
        if not os.isatty(0):
            raise ValueError("attended mode requires an interactive terminal")
        names = {"codex": "codex", "claude": "claude", "cursor": "cursor-agent", "hermes": "hermes"}
        executable = shutil.which(names[host]) or names[host]
        if host == "hermes":
            argv = [executable, "chat", "-q", prompt, "-t", "terminal,file"]
            if model:
                argv.extend(("--model", model))
            if effort:
                argv.extend(("--reasoning", effort))
            return argv
        argv = [executable]
        if host == "codex":
            argv.extend(("--ignore-user-config", "--ignore-rules"))
        elif host == "claude":
            argv.extend(("--disable-slash-commands", "--strict-mcp-config", "--setting-sources", "project"))
        if host == "claude" and session_id:
            argv.extend(("--session-id", session_id))
        if model:
            argv.extend(("--model", model))
        if effort and host == "claude":
            argv.extend(("--effort", effort))
        argv.append(prompt)
        return argv
    if host == "codex":
        argv = ["codex", "exec", "--json", "--color", "never", "--sandbox", "workspace-write", "--approve-for-me",
                "--ignore-user-config", "--ignore-rules", "-C", str(workspace)]
        if model and model.lower() not in ("inherit", "host default"):
            argv.extend(("-m", model))
        if effort:
            argv.extend(("-c", f"model_reasoning_effort={effort}"))
    elif host == "claude":
        argv = ["claude", "-p", "--output-format", "json", "--permission-mode", "acceptEdits",
                "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config",
                "--setting-sources", "project"]
        for tool in sorted(set(allowlist or ())):
            argv.extend(("--allowedTools", tool))
        if model:
            argv.extend(("--model", model))
        if effort:
            argv.extend(("--effort", effort))
    elif host == "cursor":
        argv = ["cursor-agent", "-p", "--output-format", "json", "--sandbox", "enabled", "--trust",
                "--workspace", str(workspace)]
        if model:
            if model.endswith("-fast"):
                raise ValueError("Cursor fast model variants are disabled for supervised runs")
            argv.extend(("--model", model))
    else:
        argv = ["hermes", "-z", prompt, "--in", str(workspace)]
        argv.extend(("-t", "terminal,file"))
        if model:
            argv.extend(("-m", model))
        if effort:
            argv.extend(("--reasoning", effort))
        if usage_file:
            argv.extend(("--usage-file", str(usage_file)))
        return argv
    argv.append(prompt)
    return argv


def _usage(value: dict[str, Any], mapping: dict[str, str]) -> dict[str, int]:
    result = {}
    for target, source in mapping.items():
        item = value.get(source)
        if type(item) is int and item >= 0:
            result[target] = item
    return result


def parse_events(host: str, text: str) -> dict[str, Any]:
    """Normalize supported host result formats; preserve denial and error signals."""
    if host == "codex":
        final, usage, model, session_id, calls = "", {}, None, None, 0
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
                usage.update(_usage(turn_usage, {"input": "input_tokens", "cache_read": "cached_input_tokens",
                    "cache_creation": "cache_write_input_tokens", "output": "output_tokens", "thinking": "reasoning_output_tokens"}))
                model = (event.get("model_provider") or {}).get("model") or event.get("model") or model
            if event.get("type") == "token_usage_record":
                payload = event.get("payload") or {}
                usage.update(_usage(payload.get("turn_token_usage") or payload.get("usage") or event.get("usage") or {},
                    {"input": "input_tokens", "cache_read": "cached_input_tokens", "cache_creation": "cache_write_input_tokens",
                     "output": "output_tokens", "thinking": "reasoning_output_tokens"}))
                session_id = payload.get("session_id") or session_id
        return {"text": final, "usage": usage, "model_id": model, "session_id": session_id, "calls": calls}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if host == "claude":
        usage = data.get("usage") or {}
        return {"text": data.get("structured_output") or data.get("result", ""), "usage": _usage(usage, {"input": "input_tokens", "output": "output_tokens",
                "cache_read": "cache_read_input_tokens", "cache_creation": "cache_creation_input_tokens"}),
                "model_id": data.get("model") or next(iter(data.get("modelUsage") or {}), None),
                "session_id": data.get("session_id"), "calls": 1,
                "host_reported_cost_usd": data.get("total_cost_usd"), "denied_actions": data.get("permission_denials", []),
                "is_error": data.get("is_error", False)}
    if host == "cursor":
        usage = data.get("usage") or data.get("token_usage") or {}
        # Cursor Agent reports camelCase counters; older snake_case names are kept as a fallback.
        counters = {**_usage(usage, {"input": "input_tokens", "output": "output_tokens",
                                     "cache_read": "cache_read_tokens", "cache_creation": "cache_write_tokens"}),
                    **_usage(usage, {"input": "inputTokens", "output": "outputTokens",
                                     "cache_read": "cacheReadTokens", "cache_creation": "cacheWriteTokens"})}
        return {"text": data.get("result") or data.get("text", ""), "usage": counters,
                "model_id": data.get("model"), "session_id": data.get("session_id"), "calls": 1,
                "denied_actions": data.get("permission_denials", []), "is_error": data.get("is_error", False)}
    return {"text": data.get("response", ""), "usage": _usage(data, {"input": "input_tokens", "output": "output_tokens",
            "thinking": "reasoning_tokens", "cache_read": "cache_read_tokens", "cache_creation": "cache_write_tokens"}),
            "model_id": data.get("model"), "session_id": data.get("session_id"), "calls": data.get("api_calls", 1),
            "host_reported_cost_usd": data.get("estimated_cost_usd"), "is_error": data.get("failed", False)}


def resolve_model(root: Path, workspace: Path, feature: str, tier: str, host: str) -> dict[str, Any]:
    import subprocess

    proc = subprocess.run([str(root / "scripts/resolve-model.sh"), "--platform", host, "--tier", tier,
                           "--workspace", str(workspace), "--feature", feature], cwd=workspace,
                          text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "model resolution failed")
    result = json.loads(proc.stdout)
    if not isinstance(result, dict) or result.get("error"):
        raise RuntimeError(str(result.get("error", "invalid model resolution")))
    return result


def environment(host: str, *, feature: str | None = None, attempt_id: str | None = None,
                session_file: Path | None = None) -> dict[str, str]:
    env = {**os.environ, "ADLC5_PLATFORM": host}
    if feature:
        env["ADLC5_RUNNER_FEATURE"] = feature
    if attempt_id:
        env["ADLC5_RUNNER_ATTEMPT_ID"] = attempt_id
    if session_file:
        env["ADLC5_RUNNER_SESSION_FILE"] = str(session_file)
    return env
