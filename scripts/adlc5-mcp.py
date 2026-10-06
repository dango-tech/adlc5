#!/usr/bin/env python3
"""Thin MCP stdio server — transport only over ./scripts/adlc5 (no second engine).

Run (stdio):
  python3 ./scripts/adlc5-mcp.py

Smoke (no MCP client):
  python3 ./scripts/adlc5-mcp.py --smoke

Cursor / Claude MCP config example:
  {
    "mcpServers": {
      "adlc5": {
        "command": "python3",
        "args": ["/absolute/path/to/adlc5/scripts/adlc5-mcp.py"]
      }
    }
  }

See: docs/ADLC5-kernel.md
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ADLC5 = ROOT / "scripts" / "adlc5"
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "adlc5-kernel"
SERVER_VERSION_FILE = ROOT / "core" / "VERSION"

# Tool name → (cli argv builder)
TOOL_SPECS: dict[str, dict[str, Any]] = {
    "adlc5_version": {
        "description": "Print ADLC5 semver (→ adlc5 version)",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "build": lambda _a: ["version"],
    },
    "adlc5_gate": {
        "description": "Evaluate delivery/lifecycle gates (→ adlc5 gate)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "gate": {"type": "string"},
                "workspace": {"type": "string"},
                "write_gate_summary": {"type": "boolean"},
            },
            "required": ["feature"],
            "additionalProperties": False,
        },
        "build": lambda a: _args_gate(a),
    },
    "adlc5_pack": {
        "description": "Generate story context pack (→ adlc5 pack)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "story_id": {"type": "string"},
                "workspace": {"type": "string"},
                "persona": {"type": "string", "enum": ["coder", "tester"]},
            },
            "required": ["feature", "story_id"],
            "additionalProperties": False,
        },
        "build": lambda a: _args_pack(a),
    },
    "adlc5_clarity": {
        "description": "Score a spec/design file (→ adlc5 clarity)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "step_id": {"type": "string"},
            },
            "required": ["file_path"],
            "additionalProperties": False,
        },
        "build": lambda a: _args_clarity(a),
    },
    "adlc5_phase": {
        "description": "Suggest/validate phase advance (→ adlc5 phase; suggest-only)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "workspace": {"type": "string"},
                "target": {"type": "string"},
            },
            "required": ["feature"],
            "additionalProperties": False,
        },
        "build": lambda a: _args_phase(a),
    },
    "adlc5_pilot": {
        "description": "One autopilot iteration (→ adlc5 pilot)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "workspace": {"type": "string"},
                "record_result": {"type": "string", "enum": ["pass", "fail"]},
            },
            "required": ["feature"],
            "additionalProperties": False,
        },
        "build": lambda a: _args_pilot(a),
    },
    "adlc5_state_get": {
        "description": "Read feature state.json (→ adlc5 state get)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "workspace": {"type": "string"},
            },
            "required": ["feature"],
            "additionalProperties": False,
        },
        "build": lambda a: ["state", "get", "--feature", a["feature"], * _opt("--workspace", a.get("workspace"))],
    },
    "adlc5_transition": {
        "description": "Validated canonical next step; completion requires fresh evidence",
        "inputSchema": {"type": "object", "properties": {"feature": {"type": "string"}, "workspace": {"type": "string"}, "target": {"type": "string"}}, "required": ["feature", "target"], "additionalProperties": False},
        "build": lambda a: ["transition", a["target"], "--feature", a["feature"], *_opt("--workspace", a.get("workspace"))],
    },
    "adlc5_evidence": {
        "description": "Run declared checks or record local reviewer/approval attestation",
        "inputSchema": {"type": "object", "properties": {"feature": {"type": "string"}, "workspace": {"type": "string"}, "action": {"enum": ["check", "review", "approve", "build"]}, "file": {"type": "string"}}, "required": ["feature", "action"], "additionalProperties": False},
        "build": lambda a: ["evidence", a["action"], "--feature", a["feature"], *_opt("--workspace", a.get("workspace")), *_opt("--file", a.get("file"))],
    },
    "adlc5_state_set": {
        "description": "Schema-validated metadata patch/replace; progression/results use transition/evidence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feature": {"type": "string"},
                "workspace": {"type": "string"},
                "patch": {"type": "string", "description": "JSON object string to merge"},
                "file": {"type": "string", "description": "Path to JSON file"},
                "replace": {"type": "boolean"},
                "dry_run": {"type": "boolean"},
            },
            "required": ["feature"],
            "additionalProperties": False,
        },
        "build": lambda a: _args_state_set(a),
    },
    "adlc5_resolve_model": {
        "description": "Resolve tier → host model ID (→ adlc5 resolve-model)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tier": {"type": "string"},
                "platform": {"type": "string"},
                "step": {"type": "string"},
                "workspace": {"type": "string"},
                "feature": {"type": "string"},
            },
            "required": ["tier"],
            "additionalProperties": False,
        },
        "build": lambda a: _args_resolve(a),
    },
    "adlc5_repo_spec": {
        "description": "Initialize, reconcile, or validate tracked repository constitution",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["init", "reconcile", "validate"]},
                "workspace": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
        "build": lambda a: ["repo-spec", a["action"], *_opt("--workspace", a.get("workspace"))],
    },
    "adlc5_repo_index": {
        "description": "Build/refresh/check generated repository intelligence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["build", "refresh", "check"]},
                "workspace": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
        "build": lambda a: ["repo-index", a["action"], *_opt("--workspace", a.get("workspace"))],
    },
}


def _opt(flag: str, value: Any) -> list[str]:
    if value is None or value == "":
        return []
    return [flag, str(value)]


def _args_gate(a: dict[str, Any]) -> list[str]:
    out = ["gate", "--feature", a["feature"], *_opt("--gate", a.get("gate")), *_opt("--workspace", a.get("workspace"))]
    if a.get("write_gate_summary"):
        out.append("--write-gate-summary")
    return out


def _args_pack(a: dict[str, Any]) -> list[str]:
    return [
        "pack",
        "--feature",
        a["feature"],
        "--story-id",
        a["story_id"],
        *_opt("--workspace", a.get("workspace")),
        *_opt("--persona", a.get("persona")),
    ]


def _args_clarity(a: dict[str, Any]) -> list[str]:
    out = ["clarity", a["file_path"]]
    if a.get("step_id"):
        out.extend(["--step-id", a["step_id"]])
    return out


def _args_phase(a: dict[str, Any]) -> list[str]:
    return [
        "phase",
        "--feature",
        a["feature"],
        *_opt("--workspace", a.get("workspace")),
        *_opt("--target", a.get("target")),
    ]


def _args_pilot(a: dict[str, Any]) -> list[str]:
    return [
        "pilot",
        "--feature",
        a["feature"],
        *_opt("--workspace", a.get("workspace")),
        *_opt("--record-result", a.get("record_result")),
    ]


def _args_state_set(a: dict[str, Any]) -> list[str]:
    out = ["state", "set", "--feature", a["feature"], *_opt("--workspace", a.get("workspace"))]
    if a.get("file"):
        out.extend(["--file", a["file"]])
    elif a.get("patch") is not None:
        patch = a["patch"]
        if not isinstance(patch, str):
            patch = json.dumps(patch)
        out.extend(["--patch", patch])
    else:
        raise ValueError("adlc5_state_set requires patch or file")
    if a.get("replace"):
        out.append("--replace")
    if a.get("dry_run"):
        out.append("--dry-run")
    return out


def _args_resolve(a: dict[str, Any]) -> list[str]:
    return [
        "resolve-model",
        "--tier",
        a["tier"],
        *_opt("--platform", a.get("platform")),
        *_opt("--step", a.get("step")),
        *_opt("--workspace", a.get("workspace")),
        *_opt("--feature", a.get("feature")),
    ]


def read_version() -> str:
    if SERVER_VERSION_FILE.is_file():
        return SERVER_VERSION_FILE.read_text(encoding="utf-8").strip()
    return "0.0.0"


def invoke_adlc5(argv: list[str]) -> dict[str, Any]:
    if not ADLC5.is_file():
        return {"ok": False, "exit_code": 2, "stdout": "", "stderr": f"missing façade: {ADLC5}"}
    proc = subprocess.run(
        [sys.executable, str(ADLC5), *argv],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "argv": ["adlc5", *argv],
    }


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": spec["description"],
            "inputSchema": spec["inputSchema"],
        }
        for name, spec in TOOL_SPECS.items()
    ]


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    if name not in TOOL_SPECS:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
        }
    args = arguments or {}
    try:
        argv = TOOL_SPECS[name]["build"](args)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Invalid arguments: {exc}"}],
        }
    result = invoke_adlc5(argv)
    payload = {
        "exit_code": result["exit_code"],
        "argv": result["argv"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }
    text = json.dumps(payload, indent=2)
    return {
        "isError": not result["ok"],
        "content": [{"type": "text", "text": text}],
    }


# --- Minimal JSON-RPC MCP (Content-Length framing) ---


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8").strip()
        if ":" in decoded:
            k, v = decoded.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(msg: dict[str, Any]) -> None:
    body = json.dumps(msg, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _respond(req_id: Any, result: Any) -> None:
    _write_message({"jsonrpc": "2.0", "id": req_id, "result": result})


def _respond_error(req_id: Any, code: int, message: str) -> None:
    _write_message(
        {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
    )


def handle_request(msg: dict[str, Any]) -> None:
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}

    # Notifications have no id
    if req_id is None:
        return

    if method == "initialize":
        _respond(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": read_version()},
            },
        )
        return

    if method == "ping":
        _respond(req_id, {})
        return

    if method == "tools/list":
        _respond(req_id, {"tools": list_tools()})
        return

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            _respond_error(req_id, -32602, "tools/call requires name")
            return
        _respond(req_id, call_tool(name, arguments if isinstance(arguments, dict) else {}))
        return

    _respond_error(req_id, -32601, f"Method not found: {method}")


def serve_stdio() -> int:
    while True:
        try:
            msg = _read_message()
        except (json.JSONDecodeError, ValueError) as exc:
            _write_message(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"},
                }
            )
            continue
        if msg is None:
            return 0
        handle_request(msg)


def smoke() -> int:
    tools = list_tools()
    names = {t["name"] for t in tools}
    expected = set(TOOL_SPECS)
    if names != expected:
        print(f"FAIL: tool set mismatch missing={expected - names} extra={names - expected}", file=sys.stderr)
        return 1
    ver = invoke_adlc5(["version"])
    if ver["exit_code"] != 0 or "adlc5 " not in ver["stdout"]:
        print(f"FAIL: version invoke: {ver}", file=sys.stderr)
        return 1
    # JSON-RPC tools/list roundtrip via framing helpers (in-process)
    listed = call_tool("adlc5_version", {})
    if listed.get("isError"):
        print(f"FAIL: adlc5_version tool: {listed}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "tools": sorted(names), "version": ver["stdout"].strip()}))
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] == "--smoke":
        return smoke()
    return serve_stdio()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
