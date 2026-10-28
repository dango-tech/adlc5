#!/usr/bin/env python3
"""Choose per-host model tiers and inspect effective ADLC5 configuration."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.config_layers import config_paths, merge, effective_config
from lib.model_routing import load_yaml_file
from runner.hosts import AVAILABLE_MODES, MODES

EFFORTS = {
    "cost_optimized": {"reasoning": "high", "balanced": "medium", "execution": "low"},
    "balanced": {"reasoning": "high", "balanced": "medium", "execution": "medium"},
    "quality_first": {"reasoning": "xhigh", "balanced": "high", "execution": "medium"},
}
HOSTS = {"codex": "codex", "claude": "claude", "cursor": "cursor-agent", "hermes": "hermes"}


def target_path(workspace: Path, repo: bool) -> Path:
    layers = config_paths(workspace)
    return next(path for name, path in layers if name == ("project" if repo else "master"))


def read_effective(workspace: Path) -> tuple[dict, dict[str, Path]]:
    values, rows = effective_config(workspace)
    sources = {row['key'].split('.')[0]: Path(row['source']) for row in rows}
    return values, sources


def show(workspace: Path) -> int:
    config, sources = read_effective(workspace)
    profiles = config.get("platform_profiles") if isinstance(config.get("platform_profiles"), dict) else {}
    defaults = config.get("defaults") if isinstance(config.get("defaults"), dict) else {}
    result = {
        "default_host": {"value": config.get("default_host", "codex"), "source": str(sources.get("default_host", "built-in"))},
        "preset": {"value": (config.get("model_routing") or {}).get("strategy", "balanced"), "source": str(sources.get("model_routing", "built-in"))},
        "summary": {"value": defaults.get("summary", "brief"), "source": str(sources.get("defaults", "built-in"))},
        "platform_profiles": {"value": profiles, "source": str(sources.get("platform_profiles", "built-in"))},
        "platform_modes": {"value": config.get("platform_modes", {}), "source": str(sources.get("platform_modes", "built-in"))},
    }
    print(json.dumps(result, indent=2))
    return 0


def answer(prompt: str, default: str, accept_defaults: bool) -> str:
    if accept_defaults:
        return default
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def cursor_models() -> list[str]:
    proc = subprocess.run(["cursor-agent", "models"], text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "could not list Cursor account models")
    models = [line.split()[0] for line in proc.stdout.splitlines()
              if line.strip() and not line.startswith("Available models") and not line.split()[0].endswith("-fast")]
    return models


def setup(workspace: Path, repo: bool, accept_defaults: bool, host: str) -> int:
    if host not in HOSTS:
        raise ValueError("host must be codex, claude, cursor, or hermes")
    if not shutil.which(HOSTS[host]):
        raise RuntimeError(f"{HOSTS[host]} CLI is not installed or not on PATH")
    effective, _ = read_effective(workspace)
    strategy_default = str((effective.get("model_routing") or {}).get("strategy", "balanced"))
    strategy = answer("Preset (cost_optimized, balanced, quality_first)", strategy_default, accept_defaults)
    if strategy not in EFFORTS:
        raise ValueError("preset must be cost_optimized, balanced, or quality_first")
    inherited = ((effective.get("platform_profiles") or {}).get(host) or {})
    current_mode = ((effective.get("platform_modes") or {}).get(host) or MODES[host][0])
    mode = answer(f"{host.title()} supervision mode ({', '.join(AVAILABLE_MODES[host])})", current_mode, accept_defaults)
    if mode not in AVAILABLE_MODES[host]:
        raise ValueError(f"unsupported {host} supervision mode: {mode}")
    available = cursor_models() if host == "cursor" else []
    profile = {}
    for tier, effort_default in EFFORTS[strategy].items():
        old = inherited.get(tier) if isinstance(inherited, dict) else None
        old_model = old.get("model", "host default") if isinstance(old, dict) else "host default"
        old_effort = old.get("effort", effort_default) if isinstance(old, dict) else effort_default
        choices = " (fast variants excluded: " + ", ".join(available) + ")" if host == "cursor" else ""
        model = answer(f"{host.title()} {tier} model{choices} (use 'host default' to inherit)", str(old_model), accept_defaults)
        if model.lower() in ("default", "host default"):
            model = "host default"
        if host == "cursor" and model != "host default":
            if model not in available:
                raise ValueError(f"Cursor model {model!r} is not in the account model list (fast variants are excluded)")
            effort = next((level for level in ("low", "medium", "high", "xhigh")
                           if model.endswith("-" + level)), old_effort)
        else:
            effort = answer(f"{host.title()} {tier} reasoning effort", str(old_effort), accept_defaults)
        if effort not in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
            raise ValueError(f"unsupported {host} effort: {effort}")
        profile[tier] = {"model": model, "effort": effort}
    summary = answer("End-of-run summary (off, brief, detailed)", str((effective.get("defaults") or {}).get("summary", "brief")), accept_defaults)
    if summary not in ("off", "brief", "detailed"):
        raise ValueError("summary must be off, brief, or detailed")
    verifier_default = bool((effective.get("persona_mode") or {}).get("verifier_different_model", False))
    verifier_different = answer("Use a different model for verification? (yes/no)", "yes" if verifier_default else "no", accept_defaults)
    if verifier_different.lower() not in ("yes", "no"):
        raise ValueError("verifier model choice must be yes or no")
    verifier_different = verifier_different.lower() == "yes"

    path = target_path(workspace, repo)
    current = load_yaml_file(path)
    current.pop("model_profiles", None)
    routing = current.setdefault("model_routing", {})
    if isinstance(routing, dict):
        routing.pop("execution_policy", None)
        routing["strategy"] = strategy
    if not repo:
        current["config_version"] = 1
        current["default_host"] = host
        current.setdefault("defaults", {})["summary"] = summary
        current.setdefault("platform_profiles", {})[host] = profile
        current.setdefault("platform_modes", {})[host] = mode
        current.setdefault("persona_mode", {})["verifier_different_model"] = verifier_different
    else:
        master = load_yaml_file(target_path(workspace, False))
        master_routing = master.get("model_routing") if isinstance(master.get("model_routing"), dict) else {}
        master_defaults = master.get("defaults") if isinstance(master.get("defaults"), dict) else {}
        master_profile = (master.get("platform_profiles") or {}).get(host, {})
        master_mode = (master.get("platform_modes") or {}).get(host, MODES[host][0])
        if strategy == master_routing.get("strategy", "balanced"):
            if isinstance(routing, dict):
                routing.pop("strategy", None)
                if not routing:
                    current.pop("model_routing", None)
        if summary == master_defaults.get("summary", "brief"):
            defaults = current.get("defaults")
            if isinstance(defaults, dict):
                defaults.pop("summary", None)
                if not defaults:
                    current.pop("defaults", None)
        master_verifier = bool((master.get("persona_mode") or {}).get("verifier_different_model", False))
        persona_mode = current.setdefault("persona_mode", {})
        if verifier_different == master_verifier:
            persona_mode.pop("verifier_different_model", None)
        else:
            persona_mode["verifier_different_model"] = verifier_different
        if not persona_mode:
            current.pop("persona_mode", None)
        overrides = {tier: value for tier, value in profile.items() if value != (master_profile or {}).get(tier)}
        platform_profiles = current.setdefault("platform_profiles", {})
        if overrides:
            platform_profiles[host] = overrides
        else:
            platform_profiles.pop(host, None)
        if not platform_profiles:
            current.pop("platform_profiles", None)
        modes = current.setdefault("platform_modes", {})
        if mode == master_mode:
            modes.pop(host, None)
        else:
            modes[host] = mode
        if not modes:
            current.pop("platform_modes", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "path": str(path), "host": host, "preset": strategy}, indent=2))
    return 0


SETTABLE = ("default_host", "model_routing", "platform_profiles", "platform_modes", "persona_mode", "defaults", "git_branch_prefix")


def set_value(workspace: Path, scope: str, key: str, raw: str) -> int:
    """Write one dotted setting into the machine, project or worktree layer (the Pulse Settings page builds this command)."""
    parts = key.split(".")
    if parts[0] not in SETTABLE or not all(parts):
        raise ValueError(f"unsupported setting: {key}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    path = next(path for name, path in config_paths(None if scope == "machine" else workspace) if name == {"machine": "master"}.get(scope, scope))
    if path.is_symlink():
        raise ValueError("refusing to write through a symlinked configuration file")
    current = load_yaml_file(path) if path.exists() else {}
    node = current
    for part in parts[:-1]:
        node = node.setdefault(part, {}) if isinstance(node.get(part), dict) or part not in node else None
        if node is None:
            raise ValueError(f"{key} is nested under a non-mapping value")
    node[parts[-1]] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "path": str(path), "key": key, "value": value}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "setup", "set"))
    parser.add_argument("key", nargs="?", help="set: dotted setting key, e.g. defaults.summary")
    parser.add_argument("value", nargs="?", help="set: JSON value or plain string")
    parser.add_argument("--scope", choices=("machine", "project", "worktree"), default="machine", help="set: layer to write")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--repo", action="store_true", help="write repository layer instead of master")
    parser.add_argument("--host", choices=tuple(HOSTS), default="codex", help="host profile to configure")
    parser.add_argument("--accept-defaults", action="store_true", help="use current or documented defaults without prompting")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    try:
        if args.action == "set":
            if args.key is None or args.value is None:
                parser.error("set requires KEY and VALUE")
            return set_value(workspace, args.scope, args.key, args.value)
        return show(workspace) if args.action == "show" else setup(workspace, args.repo, args.accept_defaults, args.host)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
