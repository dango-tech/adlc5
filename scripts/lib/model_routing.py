"""Resolve ADLC5 abstract model tiers to host model IDs (no required PyYAML)."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

VALID_TIERS = ("reasoning", "balanced", "execution", "implementation", "fast")
TIER_ALIAS = {"implementation": "execution"}
PLATFORMS = ("cursor", "claude", "codex", "opencode", "hermes", "gemini", "antigravity")


def _merge_dict(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if not s:
        return ""
    if s.startswith(("'", '"')) and s.endswith(("'", '"')) and len(s) >= 2:
        return s[1:-1]
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def _parse_nested_yaml(text: str) -> dict:
    """Indentation-based subset parser for ADLC5 config shapes."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- "):
            item_raw = content[2:].strip()
            if not isinstance(parent, list):
                continue
            if ":" in item_raw and not item_raw.startswith(("'", '"')):
                key, _, val = item_raw.partition(":")
                key = key.strip()
                val = val.strip()
                if val == "":
                    child: dict[str, Any] = {}
                    parent.append(child)
                    stack.append((indent, child))
                else:
                    parent.append({key: _parse_scalar(val)})
            else:
                parent.append(_parse_scalar(item_raw))
            continue

        if ":" not in content:
            continue
        key, _, val = content.partition(":")
        key = key.strip()
        val = val.strip()
        if not isinstance(parent, dict):
            continue
        if val == "":
            # Peek next non-empty line to decide list vs map
            child_map: dict[str, Any] = {}
            parent[key] = child_map
            stack.append((indent, child_map))
        else:
            parent[key] = _parse_scalar(val)

    return root


def load_yaml_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return _parse_nested_yaml(text)


def read_version(root: Path) -> str:
    version_path = root / "core" / "VERSION"
    if version_path.is_file():
        return version_path.read_text(encoding="utf-8").strip()
    return "0.0.0"


def normalize_tier(tier: str) -> str:
    t = (tier or "").strip().lower()
    if t not in VALID_TIERS:
        raise ValueError(f"invalid tier '{tier}'; expected one of: {', '.join(VALID_TIERS)}")
    return TIER_ALIAS.get(t, t)


def detect_platform(explicit: str | None = None) -> str:
    if explicit:
        p = explicit.strip().lower()
        if p not in PLATFORMS and p != "unknown":
            raise ValueError(f"invalid platform '{explicit}'; expected one of: {', '.join(PLATFORMS)}")
        return p

    env = os.environ
    # Explicit ADLC5 hint first
    hint = (env.get("ADLC5_PLATFORM") or env.get("ADLC5_HOST") or "").strip().lower()
    if hint in PLATFORMS:
        return hint

    # Host-specific env markers (heuristic — document limitations)
    if env.get("CURSOR_AGENT") or env.get("CURSOR_TRACE_ID") or "cursor" in (env.get("TERM_PROGRAM") or "").lower():
        return "cursor"
    if env.get("CLAUDECODE") or env.get("CLAUDE_CODE") or env.get("ANTHROPIC_API_KEY") and env.get("CLAUDE_PLUGIN_ROOT"):
        return "claude"
    if env.get("CODEX_HOME") or env.get("CODEX_CI") or "codex" in (env.get("npm_lifecycle_event") or "").lower():
        return "codex"
    if env.get("OPENCODE") or env.get("OPENCODE_CONFIG"):
        return "opencode"
    if env.get("HERMES_HOME") or env.get("HERMES_AGENT"):
        return "hermes"
    if env.get("GEMINI_CLI") or env.get("ANTIGRAVITY") or "gemini" in (env.get("TERM_PROGRAM") or "").lower():
        return "gemini"

    # argv0 / process hints
    for key in ("CURSOR_SESSION_ID", "VSCODE_PID"):
        if env.get(key):
            return "cursor"

    return "unknown"


def merge_model_config(root: Path, workspace: Path | None) -> dict:
    cfg: dict[str, Any] = {}
    example = root / "config.example.yaml"
    user = root / "config.yaml"
    cfg = _merge_dict(cfg, load_yaml_file(example))
    cfg = _merge_dict(cfg, load_yaml_file(user))
    if workspace is not None:
        ws_cfg = workspace / ".adlc5" / "config.yaml"
        cfg = _merge_dict(cfg, load_yaml_file(ws_cfg))
    return cfg


def _feature_policy_knobs(workspace: Path | None, feature: str | None) -> dict[str, Any]:
    """Persona spawn knobs + model-routing override read from feature policies.yaml.

    execution_policy here is a *feature-level* override: a policy profile
    (e.g. templates/policies-tiny.yaml.example, policies-standard.yaml.example)
    may set `model_routing.execution_policy: explicit` to route
    implement-1-build subagents to the cheap execution tier for that feature
    regardless of the global config.yaml default (which stays "inherit" —
    the safe, opt-in-per-profile default). High-risk profiles should leave
    this unset or set it to "inherit" explicitly.
    """
    if workspace is None or not feature:
        return {}
    try:
        from lib.policies_load import load_policies
    except Exception:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from lib.policies_load import load_policies  # type: ignore

    policies = load_policies(workspace, feature)
    persona = policies.get("persona_mode") or {}
    routing = policies.get("model_routing") or {}
    return {
        "fresh_session": bool(persona.get("fresh_session_per_persona")),
        "verifier_different_model": bool(persona.get("verifier_different_model")),
        "persona_mode": bool(persona.get("enabled")),
        "execution_policy": str(routing.get("execution_policy") or "").strip().lower() or None,
    }


def resolve_model(
    *,
    root: Path,
    tier: str,
    platform: str | None = None,
    workspace: Path | None = None,
    feature: str | None = None,
    step: str | None = None,
) -> dict[str, Any]:
    canonical = normalize_tier(tier)
    plat = detect_platform(platform)
    cfg = merge_model_config(root, workspace)
    version = read_version(root)

    routing = cfg.get("model_routing") or {}
    if not isinstance(routing, dict):
        routing = {}

    knobs = _feature_policy_knobs(workspace, feature)
    execution_policy_source = "config"
    raw_execution_policy = routing.get("execution_policy")
    if knobs.get("execution_policy"):
        raw_execution_policy = knobs["execution_policy"]
        execution_policy_source = "feature_policy"
    execution_policy = str(raw_execution_policy or "inherit").strip().lower()
    if execution_policy not in ("inherit", "explicit"):
        execution_policy = "inherit"
    strategy = str(routing.get("strategy") or "balanced").strip().lower()

    profiles = cfg.get("platform_profiles") or {}
    flat = cfg.get("model_profiles") or {}
    if not isinstance(profiles, dict):
        profiles = {}
    if not isinstance(flat, dict):
        flat = {}

    plat_cfg = profiles.get(plat) if plat != "unknown" else None
    if not isinstance(plat_cfg, dict):
        plat_cfg = {}

    spawn = plat_cfg.get("spawn") if isinstance(plat_cfg.get("spawn"), dict) else {}

    def _lookup(keys: tuple[str, ...], containers: list[tuple[str, dict]]) -> tuple[str | None, str]:
        for label, container in containers:
            for key in keys:
                if key in container and not isinstance(container[key], dict):
                    return str(container[key]).strip(), f"{label}.{key}"
        return None, "none"

    # execution_policy inherit: prefer legacy flat implementation/execution (usually "inherit")
    # execution_policy explicit: prefer platform_profiles concrete IDs
    if canonical == "execution" and execution_policy == "inherit":
        model_id, source = _lookup(
            ("implementation", "execution"),
            [("model_profiles", flat), (f"platform_profiles.{plat}", plat_cfg)],
        )
        if model_id is None:
            model_id, source = "inherit", "execution_policy.inherit"
        else:
            source = f"{source}+execution_policy.inherit"
    elif canonical == "execution" and execution_policy == "explicit":
        model_id, source = _lookup(
            ("execution", "implementation"),
            [(f"platform_profiles.{plat}", plat_cfg), ("model_profiles", flat)],
        )
        if model_id is None or model_id.lower() == "inherit":
            bal, bal_src = _lookup(("balanced",), [(f"platform_profiles.{plat}", plat_cfg), ("model_profiles", flat)])
            if bal and bal.lower() != "inherit":
                model_id, source = bal, f"{bal_src}+execution_policy.explicit"
            elif model_id is None:
                model_id, source = "", "default+execution_policy.explicit"
            else:
                source = f"{source}+execution_policy.explicit"
        else:
            source = f"{source}+execution_policy.explicit"
    else:
        model_id, source = _lookup(
            (canonical, "implementation" if canonical == "execution" else canonical),
            [(f"platform_profiles.{plat}", plat_cfg), ("model_profiles", flat)],
        )
        if model_id is None:
            model_id, source = ("inherit" if canonical == "execution" else ""), "default"

    model_id = str(model_id).strip() if model_id is not None else ""

    fresh_session = bool(spawn.get("fresh_session_per_persona")) or bool(knobs.get("fresh_session"))

    notice_parts = [
        f"Recommended model tier: {canonical} (alias ok: implementation→execution).",
        f"Resolved via ./scripts/resolve-model.sh → {model_id or '(empty)'}.",
        "See core/guides/model-matrix.md and config platform_profiles / model_profiles.",
        "Never use fast for implement/verify or @qa.",
    ]
    if plat == "unknown":
        notice_parts.append("Platform undetected — used flat model_profiles fallback.")
    if step:
        notice_parts.append(f"Step context: {step}.")
    if execution_policy_source == "feature_policy":
        notice_parts.append(f"execution_policy={execution_policy} from feature policies.yaml (overrides config.yaml).")

    return {
        "tier": canonical,
        "requested_tier": tier,
        "model_id": model_id,
        "spawn_policy": spawn,
        "fresh_session": fresh_session,
        "platform": plat,
        "notice": " ".join(notice_parts),
        "version": version,
        "execution_policy": execution_policy,
        "execution_policy_source": execution_policy_source,
        "strategy": strategy,
        "source": source,
        "verifier_different_model": bool(knobs.get("verifier_different_model")),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Resolve ADLC5 model tier to host model ID")
    p.add_argument("--root", default="", help="adlc5 distribution root")
    p.add_argument("--platform", default="", help="cursor|claude|codex|opencode|hermes|gemini|antigravity")
    p.add_argument("--tier", required=True, help="reasoning|balanced|execution|implementation|fast")
    p.add_argument("--step", default="")
    p.add_argument("--workspace", default="")
    p.add_argument("--feature", default="")
    args = p.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    workspace = Path(args.workspace).resolve() if args.workspace else None
    try:
        result = resolve_model(
            root=root,
            tier=args.tier,
            platform=args.platform or None,
            workspace=workspace,
            feature=args.feature or None,
            step=args.step or None,
        )
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
