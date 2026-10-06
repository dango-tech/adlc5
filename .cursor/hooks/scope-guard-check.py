#!/usr/bin/env python3
"""Scope-guard decision helper for Cursor preToolUse (H2).

Reads hook JSON on stdin. Prints permission JSON on stdout.
Exit 0 always (fail-open); callers treat invalid output as allow.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path

MUTATING = {
    "Write",
    "StrReplace",
    "Delete",
    "EditNotebook",
    "search_replace",
    "write",
    "delete_file",
    "edit_notebook",
}


def extract_paths(tool_input: dict) -> list[str]:
    paths: list[str] = []
    for key in ("path", "file_path", "target_notebook", "filePath"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            paths.append(value.strip())
    value = tool_input.get("paths")
    if isinstance(value, list):
        paths.extend(p for p in value if isinstance(p, str) and p.strip())
    return paths


def resolve_feature(project: Path) -> str | None:
    env_feat = (os.environ.get("ADLC5_FEATURE") or "").strip()
    if env_feat:
        return env_feat
    active = project / ".adlc5" / ".active-feature"
    if active.is_file():
        name = active.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        if name:
            return name
    return None


def load_yaml_scope_guard(path: Path) -> dict:
    """Minimal YAML subset reader for scope_guard.mode / allowed_paths."""
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    mode = None
    paths: list[str] = []
    in_sg = False
    in_paths = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("scope_guard:"):
            in_sg = True
            in_paths = False
            continue
        if in_sg and line and not line[0].isspace() and not line.startswith("scope_guard"):
            in_sg = False
            in_paths = False
        if not in_sg:
            continue
        stripped = line.strip()
        if stripped.startswith("mode:"):
            mode = stripped.split(":", 1)[1].strip().strip("\"'")
            in_paths = False
        elif stripped.startswith("allowed_paths:"):
            rest = stripped.split(":", 1)[1].strip()
            in_paths = True
            if rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1].strip()
                if inner:
                    paths.extend(p.strip().strip("\"'") for p in inner.split(","))
                in_paths = False
        elif in_paths and stripped.startswith("- "):
            paths.append(stripped[2:].strip().strip("\"'"))
        elif in_paths and line and not line[0].isspace():
            in_paths = False
    return {"mode": mode, "allowed_paths": paths}


def load_scope_meta(project: Path, feature: str) -> tuple[str | None, list[str], bool]:
    """Return (mode, allowed_paths, has_explicit_paths)."""
    feat_dir = project / ".adlc5" / feature
    allowed: list[str] = []
    mode = None
    pol = load_yaml_scope_guard(feat_dir / "policies.yaml")
    if pol.get("mode"):
        mode = pol["mode"]
    for p in pol.get("allowed_paths") or []:
        if p:
            allowed.append(p)
    state_path = feat_dir / "state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
        scope = state.get("scope") or {}
        if isinstance(scope, dict):
            for p in scope.get("allowed_paths") or []:
                if isinstance(p, str) and p.strip():
                    allowed.append(p.strip())
            if scope.get("guard_mode"):
                mode = str(scope.get("guard_mode"))
    # Always include feature tree
    allowed.append(f".adlc5/{feature}")
    seen: set[str] = set()
    uniq: list[str] = []
    for p in allowed:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    auto = {f".adlc5/{feature}", f".adlc5/{feature}/"}
    has_explicit = any(p not in auto for p in uniq)
    return mode, uniq, has_explicit


def path_in_scope(rel: str, allowed: list[str]) -> bool:
    rel_n = rel.replace("\\", "/").lstrip("./")
    for pref in allowed:
        pref_n = pref.replace("\\", "/").lstrip("./")
        if pref_n.endswith("/**"):
            pref_n = pref_n[:-3]
        elif pref_n.endswith("/*"):
            pref_n = pref_n[:-2]
        if pref_n.endswith("/"):
            pref_n = pref_n[:-1]
        if "*" in pref_n:
            if fnmatch.fnmatch(rel_n, pref_n):
                return True
            continue
        if rel_n == pref_n or rel_n.startswith(pref_n + "/"):
            return True
    return False


def decide(project: Path, data: dict) -> dict:
    tool = (data.get("tool_name") or data.get("toolName") or "").strip()
    tool_input = data.get("tool_input") or data.get("arguments") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    if tool and tool not in MUTATING:
        return {"permission": "allow"}

    paths = extract_paths(tool_input)
    feature = resolve_feature(project)
    if not paths or not feature:
        return {"permission": "allow"}

    env_mode = (os.environ.get("ADLC5_SCOPE_GUARD") or "").strip().lower()
    mode_meta, allowed, has_explicit = load_scope_meta(project, feature)
    mode = env_mode or (mode_meta or "").strip().lower() or "warn"

    if mode in ("off", "disable", "disabled", "0", "false"):
        return {"permission": "allow"}

    # Activate only when env mode, policies mode, or explicit allowed_paths exist
    explicit = bool(env_mode) or bool(mode_meta) or has_explicit
    if not explicit:
        return {"permission": "allow"}

    out_of_scope: list[str] = []
    for p in paths:
        path_obj = Path(p)
        abs_p = path_obj.resolve() if path_obj.is_absolute() else (project / path_obj).resolve()
        try:
            rel = abs_p.relative_to(project).as_posix()
        except ValueError:
            out_of_scope.append(p)
            continue
        if not path_in_scope(rel, allowed):
            out_of_scope.append(rel)

    if not out_of_scope:
        return {"permission": "allow"}

    msg = (
        f'Scope guard: path(s) outside feature "{feature}" scope: '
        + ", ".join(out_of_scope)
        + f". Allowed prefixes: {allowed}"
    )
    if mode in ("enforce", "deny", "block", "hard"):
        return {
            "permission": "deny",
            "user_message": msg,
            "agent_message": msg
            + " Stay within scope_guard.allowed_paths or ask before broadening scope.",
        }
    return {"permission": "allow", "agent_message": "WARNING: " + msg}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADLC5 scope-guard check")
    parser.add_argument("--project", default=".", help="Workspace root")
    args = parser.parse_args(argv)
    project = Path(args.project).resolve()
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return 0
    if not isinstance(data, dict):
        print(json.dumps({"permission": "allow"}))
        return 0
    print(json.dumps(decide(project, data)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
