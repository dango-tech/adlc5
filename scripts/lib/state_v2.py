"""ADLC5 unified state helpers (schema_version "3.0").

Module/symbol names keep their historical "v2" label from the schema
generation that introduced the unified state format (ADLC5 2.0). That
label is internal naming only — it is independent of the current
schema_version value ("3.0") and the framework release in core/VERSION.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "core" / "state-schema.json"


def feature_state_path(workspace: Path, feature: str) -> Path:
    return workspace / ".adlc5" / feature / "state.json"


def load_feature_state(workspace: Path, feature: str) -> dict[str, Any] | None:
    path = feature_state_path(workspace, feature)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data


def load_state_schema(schema_path: Path | None = None) -> dict[str, Any]:
    path = schema_path or SCHEMA_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(value: Any, expected: str | list[str]) -> bool:
    types = expected if isinstance(expected, list) else [expected]
    for t in types:
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "string" and isinstance(value, str):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "null" and value is None:
            return True
    return False


def validate_against_schema(
    data: Any,
    schema: dict[str, Any] | None = None,
    *,
    path: str = "$",
) -> list[str]:
    """Stdlib subset of JSON Schema (required/const/enum/type/pattern/minmax/properties/items)."""
    schema = schema if schema is not None else load_state_schema()
    errors: list[str] = []

    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {data!r}")
        return errors

    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: value {data!r} not in enum {schema['enum']}")
        return errors

    if "type" in schema and not _type_ok(data, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']}, got {type(data).__name__}")
        return errors

    if isinstance(data, str) and "pattern" in schema:
        if re.search(schema["pattern"], data) is None:
            errors.append(f"{path}: does not match pattern {schema['pattern']}")
    if isinstance(data, str) and "minLength" in schema and len(data) < schema["minLength"]:
        errors.append(f"{path}: length {len(data)} < minLength {schema['minLength']}")
    if isinstance(data, str) and "maxLength" in schema and len(data) > schema["maxLength"]:
        errors.append(f"{path}: length {len(data)} > maxLength {schema['maxLength']}")

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} > maximum {schema['maximum']}")

    if isinstance(data, dict):
        for key in schema.get("required") or []:
            if key not in data:
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            for key in data:
                if key not in props:
                    errors.append(f"{path}: unexpected property {key!r}")
        for key, value in data.items():
            if key in props and isinstance(props[key], dict):
                errors.extend(validate_against_schema(value, props[key], path=f"{path}.{key}"))

    if isinstance(data, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(data):
            errors.extend(validate_against_schema(item, schema["items"], path=f"{path}[{i}]"))

    return errors


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge dicts; non-dict patch values replace. Lists are replaced, not concatenated."""
    out: dict[str, Any] = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def set_feature_state(
    workspace: Path,
    feature: str,
    *,
    patch: dict[str, Any] | None = None,
    replace: dict[str, Any] | None = None,
    dry_run: bool = False,
    schema_path: Path | None = None,
    operation: str = "metadata",
) -> dict[str, Any]:
    """Merge or replace feature state after schema validation. Never writes on validation failure.

    Returns a result dict: {status, path, state?} or {status:error, error, errors?}.
    """
    if operation not in ("metadata", "repair", "transition"):
        return {"status": "error", "error": "invalid_operation"}
    if (patch is None) == (replace is None):
        return {
            "status": "error",
            "error": "usage",
            "message": "provide exactly one of patch or replace",
        }

    path = feature_state_path(workspace, feature)
    current = load_feature_state(workspace, feature)
    if current is None:
        return {
            "status": "error",
            "error": "state_not_found" if not path.is_file() else "invalid_json",
            "path": str(path),
        }

    if replace is not None:
        if not isinstance(replace, dict):
            return {"status": "error", "error": "invalid_replace", "message": "replace must be a JSON object"}
        candidate = replace
    else:
        if not isinstance(patch, dict):
            return {"status": "error", "error": "invalid_patch", "message": "patch must be a JSON object"}
        candidate = deep_merge(current, patch)

    # Hard invariants beyond schema — refuse identity corruption
    if candidate.get("schema_version") != "3.0":
        return {
            "status": "error",
            "error": "schema_version_locked",
            "message": "schema_version must remain \"3.0\"",
        }
    if candidate.get("feature") != feature:
        return {
            "status": "error",
            "error": "feature_mismatch",
            "message": f"state.feature must equal --feature ({feature!r})",
        }

    def protected(value, prefix=""):
        out = {}
        if isinstance(value, dict):
            for key, item in value.items():
                name = prefix + "." + key
                if key in ("current_stage", "current_step", "stage_status", "verification", "independence", "approved_by", "story_status", "current_substep") or key == "status" or key == "history" or key == "active" and prefix == ".persona":
                    out[name] = item
                else:
                    out.update(protected(item, name))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                out.update(protected(item, prefix + str(index)))
        return out
    if operation == "metadata":
        old, new = protected(current), protected(candidate)
        changed = set(old) | set(new)
        unsafe = [key for key in changed if old.get(key) != new.get(key) and not (key.endswith(".status") and new.get(key) in ("pending", "ready", "in_progress") and key not in old)]
        if unsafe:
            return {"status": "error", "error": "protected_state", "message": "use transition/evidence operations; recovery requires state repair", "fields": unsafe}
    if operation == "repair":
        # Recovery may rewind or mark work built, but never mint approval/verification.
        old = protected(current)
        for key, value in protected(candidate).items():
            if value == old.get(key):
                continue
            forbidden = key.endswith((".verification", ".independence", ".approved_by", ".history", ".story_status"))
            if key.endswith(".stage_status"):
                forbidden = any(v in ("completed", "waived") and v != (old.get(key) or {}).get(k) for k, v in value.items())
            elif isinstance(value, str) and value in ("verified", "completed", "waived"):
                forbidden = True
            if forbidden:
                return {"status": "error", "error": "repair_cannot_certify", "message": key}

    schema = load_state_schema(schema_path)
    errors = validate_against_schema(candidate, schema)
    if errors:
        return {"status": "error", "error": "schema_validation_failed", "errors": errors}

    rel = str(path)
    try:
        rel = str(path.relative_to(workspace.resolve()))
    except ValueError:
        pass

    if dry_run:
        return {"status": "ok", "dry_run": True, "path": rel, "state": candidate}

    atomic_write_json(path, candidate)
    return {"status": "ok", "path": rel, "state": candidate}


def is_v2_state(state: dict[str, Any] | None) -> bool:
    return bool(state and state.get("schema_version") == "3.0")


def iter_v2_stories(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    stories = (state.get("tasks") or {}).get("stories") or []
    out: list[tuple[str, dict[str, Any]]] = []
    if isinstance(stories, list):
        for item in stories:
            if isinstance(item, dict) and item.get("id"):
                out.append((str(item["id"]), item))
    elif isinstance(stories, dict):
        for sid, s in stories.items():
            out.append((str(sid), s if isinstance(s, dict) else {}))
    return out


def v2_to_delivery_compat(state: dict[str, Any]) -> dict[str, Any]:
    """Build delivery-shaped dict from unified state for gate handlers."""
    stories: dict[str, Any] = {}
    for sid, s in iter_v2_stories(state):
        stories[sid] = {
            "id": sid,
            "title": s.get("title", sid),
            "status": s.get("status", "pending"),
            "type": s.get("type", "component"),
            "batch": s.get("batch", 0),
            "files": s.get("files") or [],
        }
    step = state.get("current_step", "")
    phase_map = {
        "implement-1-build": "build-1-implementation",
        "implement-2-verify": "assure-1-verification",
        "implement-3-integrate": "assure-2-integration",
        "implement-4-qa": "assure-3-qa",
        "implement-5-pr": "assure-4-pr-reviewer",
    }
    current_phase = phase_map.get(step, step)
    if state.get("stage_status", {}).get("implement") == "completed":
        current_phase = "completed"
    impl = state.get("implement") or {}
    return {
        "current_phase": current_phase,
        "stories": stories,
        "integration": impl.get("integration") or {"status": "pending"},
        "phase_status": {
            "plan_discovery": "completed" if (state.get("stage_status") or {}).get("plan") == "completed" else "pending",
            "plan_code_spec": "completed" if (state.get("stage_status") or {}).get("tasks") == "completed" else "pending",
            "build_implementation": "completed"
            if all(s.get("status") in ("implementation_complete", "verified", "failed") for _, s in iter_v2_stories(state) if s.get("type") != "integration")
            else "pending",
        },
        "verification_summary": impl.get("verification") or {},
    }


V2_GATE_ALIASES: dict[str, str] = {
    "specify-complete": "specify-complete",
    "plan-complete": "plan-complete",
    "tasks-complete": "tasks-complete",
    "implement-1-build": "build-1-implementation",
    "implement-2-verify": "assure-1-verification",
    "implement-3-integrate": "assure-2-integration",
    "implement-4-qa": "assure-3-qa",
    "implement-5-pr": "assure-4-pr-reviewer",
}


def is_human_approver(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    if normalized == "user":
        return True
    if normalized.startswith("human:"):
        return bool(normalized.removeprefix("human:").strip())
    if normalized.startswith("github:"):
        return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38})", normalized.removeprefix("github:")))
    if normalized.startswith("email:"):
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized.removeprefix("email:")))
    return False
