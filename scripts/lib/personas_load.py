"""Load core/personas.yaml — step routing and memory wall validation."""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REGISTRY = ROOT / "core" / "personas.yaml"


def load_personas_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or DEFAULT_REGISTRY
    if not registry_path.is_file():
        return {}
    text = registry_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def get_persona_for_step(step: str, registry: dict[str, Any] | None = None) -> str | None:
    reg = registry or load_personas_registry()
    mapping = reg.get("step_persona") or {}
    if isinstance(mapping, dict):
        val = mapping.get(step)
        return str(val) if val else None
    return None


def get_persona_config(persona_id: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    reg = registry or load_personas_registry()
    personas = reg.get("personas") or {}
    if isinstance(personas, dict):
        cfg = personas.get(persona_id)
        return cfg if isinstance(cfg, dict) else {}
    return {}


def normalize_feature_path(path: str, feature: str) -> str:
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    prefix = f".adlc5/{feature}/"
    if p.startswith(prefix):
        return p[len(prefix) :]
    if prefix in p:
        return p.split(prefix, 1)[1]
    return p


def path_matches_pattern(rel_path: str, pattern: str) -> bool:
    rel = rel_path.replace("\\", "/").lstrip("./")
    pat = pattern.replace("\\", "/").lstrip("./")
    if pat.endswith("/"):
        return rel.startswith(pat) or fnmatch.fnmatch(rel, pat + "*")
    if fnmatch.fnmatch(rel, pat):
        return True
    if rel.startswith(pat + "/"):
        return True
    base = pat.rstrip("/")
    return rel == base


def is_feature_artifact(rel: str) -> bool:
    prefixes = ("memory/", "design/", "tasks/", "verify/", ".qa/", ".prt/", ".discover/", "spec-handoff.md", "change.md")
    return rel.startswith(prefixes) or rel in ("spec-handoff.md", "change.md")


def check_persona_context(
    persona_id: str,
    paths: list[str],
    feature: str,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = get_persona_config(persona_id, registry)
    allow = cfg.get("memory_allow") or []
    deny = cfg.get("memory_deny") or []
    violations: list[dict[str, str]] = []
    denied: list[dict[str, str]] = []

    for raw in paths:
        rel = normalize_feature_path(raw, feature)
        if deny and any(path_matches_pattern(rel, d) for d in deny):
            denied.append({"path": raw, "rel": rel, "rule": "memory_deny"})
            continue
        if allow and is_feature_artifact(rel):
            if not any(path_matches_pattern(rel, a) for a in allow):
                violations.append({"path": raw, "rel": rel, "rule": "memory_allow"})

    status = "pass" if not violations and not denied else "fail"
    return {
        "persona": persona_id,
        "status": status,
        "violations": violations,
        "denied": denied,
    }


def persona_mode_enabled(policies: dict[str, Any] | None) -> bool:
    if not policies:
        return False
    block = policies.get("persona_mode") or {}
    if isinstance(block, dict):
        return bool(block.get("enabled"))
    return False


def fresh_session_for_persona(policies: dict[str, Any] | None) -> bool:
    block = (policies or {}).get("persona_mode") or {}
    if isinstance(block, dict):
        return bool(block.get("fresh_subagent_per_persona"))
    return False


def verifier_different_model(policies: dict[str, Any] | None) -> bool:
    block = (policies or {}).get("persona_mode") or {}
    if isinstance(block, dict):
        return bool(block.get("verifier_different_model"))
    return False
