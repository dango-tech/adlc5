#!/usr/bin/env python3
"""Choose Codex model tiers and inspect the effective ADLC5 configuration."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.config_layers import config_paths, merge
from lib.model_routing import load_yaml_file

EFFORTS = {
    "cost_optimized": {"reasoning": "high", "balanced": "medium", "execution": "low"},
    "balanced": {"reasoning": "high", "balanced": "medium", "execution": "medium"},
    "quality_first": {"reasoning": "xhigh", "balanced": "high", "execution": "medium"},
}


def target_path(workspace: Path, repo: bool) -> Path:
    layers = config_paths(workspace)
    return next(path for name, path in layers if name == ("repo" if repo else "master"))


def read_effective(workspace: Path) -> tuple[dict, dict[str, Path]]:
    values: dict = {}
    sources = {}
    for name, path in config_paths(workspace):
        overlay = load_yaml_file(path)
        if overlay:
            values = merge(values, overlay)
            sources.update({key: path for key in overlay})
    return values, sources


def show(workspace: Path) -> int:
    config, sources = read_effective(workspace)
    profiles = config.get("platform_profiles") if isinstance(config.get("platform_profiles"), dict) else {}
    codex = profiles.get("codex") if isinstance(profiles.get("codex"), dict) else {}
    defaults = config.get("defaults") if isinstance(config.get("defaults"), dict) else {}
    result = {
        "default_host": {"value": config.get("default_host", "codex"), "source": str(sources.get("default_host", "built-in"))},
        "preset": {"value": (config.get("model_routing") or {}).get("strategy", "balanced"), "source": str(sources.get("model_routing", "built-in"))},
        "summary": {"value": defaults.get("summary", "brief"), "source": str(sources.get("defaults", "built-in"))},
        "platform_profiles.codex": {"value": codex, "source": str(sources.get("platform_profiles", "built-in"))},
    }
    print(json.dumps(result, indent=2))
    return 0


def answer(prompt: str, default: str, accept_defaults: bool) -> str:
    if accept_defaults:
        return default
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def setup(workspace: Path, repo: bool, accept_defaults: bool) -> int:
    if not shutil.which("codex"):
        raise RuntimeError("Codex CLI is not installed or not on PATH")
    effective, _ = read_effective(workspace)
    strategy_default = str((effective.get("model_routing") or {}).get("strategy", "balanced"))
    strategy = answer("Preset (cost_optimized, balanced, quality_first)", strategy_default, accept_defaults)
    if strategy not in EFFORTS:
        raise ValueError("preset must be cost_optimized, balanced, or quality_first")
    inherited = ((effective.get("platform_profiles") or {}).get("codex") or {})
    profile = {}
    for tier, effort_default in EFFORTS[strategy].items():
        old = inherited.get(tier) if isinstance(inherited, dict) else None
        old_model = old.get("model", "host default") if isinstance(old, dict) else "host default"
        old_effort = old.get("effort", effort_default) if isinstance(old, dict) else effort_default
        model = answer(f"Codex {tier} model (use 'host default' to inherit)", str(old_model), accept_defaults)
        if model.lower() in ("default", "host default"):
            model = "host default"
        effort = answer(f"Codex {tier} reasoning effort", str(old_effort), accept_defaults)
        if effort not in ("none", "minimal", "low", "medium", "high", "xhigh", "max"):
            raise ValueError(f"unsupported Codex effort: {effort}")
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
        current["default_host"] = "codex"
        current.setdefault("defaults", {})["summary"] = summary
        current.setdefault("platform_profiles", {})["codex"] = profile
        current.setdefault("persona_mode", {})["verifier_different_model"] = verifier_different
    else:
        master = load_yaml_file(target_path(workspace, False))
        master_routing = master.get("model_routing") if isinstance(master.get("model_routing"), dict) else {}
        master_defaults = master.get("defaults") if isinstance(master.get("defaults"), dict) else {}
        master_codex = (master.get("platform_profiles") or {}).get("codex", {})
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
        overrides = {tier: value for tier, value in profile.items() if value != (master_codex or {}).get(tier)}
        platform_profiles = current.setdefault("platform_profiles", {})
        if overrides:
            platform_profiles["codex"] = overrides
        else:
            platform_profiles.pop("codex", None)
        if not platform_profiles:
            current.pop("platform_profiles", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "path": str(path), "host": "codex", "preset": strategy}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("show", "setup"))
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--repo", action="store_true", help="write repository layer instead of master")
    parser.add_argument("--accept-defaults", action="store_true", help="use current or documented defaults without prompting")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    try:
        return show(workspace) if args.action == "show" else setup(workspace, args.repo, args.accept_defaults)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
