#!/usr/bin/env python3
"""Thin MCP stdio server — transport only over ./scripts/adlc5 (no second engine).

Run (stdio):
  python3 ./scripts/adlc5-mcp.py

Smoke (no MCP client):
  python3 ./scripts/adlc5-mcp.py --smoke

Transport: MCP stdio — newline-delimited JSON-RPC 2.0 on stdin/stdout; stdout
carries protocol messages only (diagnostics go to stderr).

Consumer workspace: every tool that touches lifecycle state resolves `workspace`
(argument → $ADLC5_WORKSPACE → $CLAUDE_PROJECT_DIR → server cwd) to an absolute
directory, runs the kernel from there, and refuses a workspace inside an
installed package. Relative file arguments resolve against that workspace.

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
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lib.package_guard import check_workspace, resolve_workspace  # noqa: E402

ADLC5 = ROOT / "scripts" / "adlc5"
SUPPORTED_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
PROTOCOL_VERSION = SUPPORTED_PROTOCOLS[0]
FEATURE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
PATH_ARGS = ("file", "file_path")
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
                "workspace": {"type": "string", "description": "Resolves a relative file_path"},
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
                "patch": {"type": ["string", "object"], "description": "JSON object (or JSON string) to merge"},
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


def default_workspace() -> Path:
    for var in ("ADLC5_WORKSPACE", "CLAUDE_PROJECT_DIR"):
        if os.environ.get(var):
            return resolve_workspace(os.environ[var])
    return Path.cwd().resolve()


def invoke_adlc5(argv: list[str], cwd: Path | None = None) -> dict[str, Any]:
    if not ADLC5.is_file():
        return {"ok": False, "exit_code": 2, "stdout": "", "stderr": f"missing façade: {ADLC5}", "argv": ["adlc5", *argv]}
    proc = subprocess.run(
        [sys.executable, str(ADLC5), *argv],
        cwd=str(cwd or default_workspace()),
        stdin=subprocess.DEVNULL,  # never let a child consume the protocol stream
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


def _type_ok(value: Any, expected: Any) -> bool:
    kinds = expected if isinstance(expected, list) else [expected]
    checks = {
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "object": lambda v: isinstance(v, dict),
    }
    return any(checks.get(k, lambda _v: True)(value) for k in kinds)


def validate_arguments(schema: dict[str, Any], args: dict[str, Any]) -> list[str]:
    errors = [f"missing required argument: {k}" for k in schema.get("required", []) if k not in args]
    props = schema.get("properties", {})
    for key, value in args.items():
        spec = props.get(key)
        if spec is None:
            if schema.get("additionalProperties") is False:
                errors.append(f"unknown argument: {key}")
            continue
        if "type" in spec and not _type_ok(value, spec["type"]):
            errors.append(f"{key} must be of type {spec['type']}")
        elif "enum" in spec and value not in spec["enum"]:
            errors.append(f"{key} must be one of {spec['enum']}")
        elif value == "" and key in schema.get("required", []):
            errors.append(f"{key} must not be empty")
    if isinstance(args.get("feature"), str) and not FEATURE_RE.fullmatch(args["feature"]):
        errors.append("feature must be a kebab-case label (letters, digits, '.', '_', '-')")
    return errors


def _tool_error(text: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": text}]}


def call_tool(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    spec = TOOL_SPECS[name]
    args = dict(arguments or {})
    errors = validate_arguments(spec["inputSchema"], args)
    if errors:
        return _tool_error("Invalid arguments: " + "; ".join(errors))

    workspace = resolve_workspace(args.get("workspace") or default_workspace())
    if "workspace" in spec["inputSchema"]["properties"]:
        problem = check_workspace(ROOT, workspace)
        if problem:
            return _tool_error(f"Invalid workspace: {problem}")
        args["workspace"] = str(workspace)
        for key in PATH_ARGS:
            if args.get(key) and not Path(args[key]).is_absolute():
                args[key] = str(workspace / args[key])
    try:
        argv = spec["build"](args)
    except (KeyError, TypeError, ValueError) as exc:
        return _tool_error(f"Invalid arguments: {exc}")
    result = invoke_adlc5(argv, cwd=workspace)
    payload = {
        "exit_code": result["exit_code"],
        "argv": result["argv"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }
    return {
        "isError": not result["ok"],
        "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
    }


# --- Minimal JSON-RPC MCP over stdio (newline-delimited messages) ---


def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_message(msg: Any) -> dict[str, Any] | None:
    """Return the JSON-RPC response for one message, or None (notification/ignored)."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
    method, req_id = msg["method"], msg.get("id")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}

    if "id" not in msg:  # notification (notifications/initialized, cancelled, ...)
        return None

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": read_version()},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list_tools()}}
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or name not in TOOL_SPECS:
            return _error(req_id, -32602, f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            return _error(req_id, -32602, "tools/call arguments must be an object")
        try:
            return {"jsonrpc": "2.0", "id": req_id, "result": call_tool(name, arguments)}
        except Exception as exc:  # keep the server alive on any tool failure
            print(f"adlc5-mcp: tool {name} failed: {exc!r}", file=sys.stderr)
            return {"jsonrpc": "2.0", "id": req_id, "result": _tool_error(f"Internal error: {exc}")}
    return _error(req_id, -32601, f"Method not found: {method}")


def _emit(msg: Any) -> None:
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def serve_stdio() -> int:
    for raw in sys.stdin.buffer:
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            _emit(_error(None, -32700, f"Parse error: {exc}"))
            continue
        if isinstance(msg, list):  # JSON-RPC batch
            replies = [r for r in (handle_message(m) for m in msg) if r is not None]
            if replies:
                _emit(replies)
        else:
            reply = handle_message(msg)
            if reply is not None:
                _emit(reply)
    return 0


def smoke() -> int:
    names = {t["name"] for t in list_tools()}
    if names != set(TOOL_SPECS):
        print(f"FAIL: tool set mismatch {names ^ set(TOOL_SPECS)}", file=sys.stderr)
        return 1
    init = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": PROTOCOL_VERSION}})
    call = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "adlc5_version", "arguments": {}}})
    if not init or "result" not in init or not call or call["result"].get("isError"):
        print(f"FAIL: protocol smoke: {init} {call}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "tools": sorted(names), "version": f"adlc5 {read_version()}"}))
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
