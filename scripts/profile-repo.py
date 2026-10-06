#!/usr/bin/env python3
"""Detect repo profile (greenfield/brownfield), size tier, and wiki action.

Usage:
  ./scripts/profile-repo.py [--workspace DIR] [--field NAME]

Fields (for --field): repo_profile, repo_size, wiki_action, detected_stack.framework

Exit 0 always on success; prints JSON to stdout.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "check_scaffold", SCRIPT_DIR / "check-scaffold.py"
)
_check_scaffold = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_check_scaffold)
check_repo_profile = _check_scaffold.check_repo_profile
detect_stack = _check_scaffold.detect_stack

IGNORE_DIRS = {
    ".git",
    ".adlc5",
    ".cursor",
    ".agents",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
    "wiki",
    "sources",
}
IGNORE_FILES = {
    ".gitignore",
    "README.md",
    "LICENSE",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "config.yaml",
    "config.example.yaml",
}
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".scala",
    ".sql",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
    ".vue",
    ".svelte",
}


def _load_project_wiki_config(workspace: Path) -> dict:
    cfg_path = workspace / ".adlc5" / "config.yaml"
    out = {
        "enabled": True,
        "auto": True,
        "ingest_on": "medium",
        "root": "wiki",
    }
    if not cfg_path.is_file():
        return out
    text = cfg_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"project_wiki:\s*\n(?:\s+enabled:\s*false|\s+#.*\n)*\s*enabled:\s*false", text):
        out["enabled"] = False
    if re.search(r"enabled:\s*false", text) and "project_wiki:" in text:
        block = text.split("project_wiki:", 1)[-1].split("\n#", 1)[0]
        if re.search(r"enabled:\s*false", block):
            out["enabled"] = False
    m = re.search(r"ingest_on:\s*(small|medium|large)", text)
    if m:
        out["ingest_on"] = m.group(1)
    m = re.search(r"auto:\s*false", text)
    if m and "project_wiki:" in text:
        out["auto"] = False
    return out


def _scan_code_files(workspace: Path) -> tuple[int, int]:
    count = 0
    total_bytes = 0
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for name in files:
            if name in IGNORE_FILES or name.startswith("."):
                continue
            path = Path(root) / name
            if path.suffix.lower() not in CODE_EXTENSIONS and path.name not in (
                "Makefile",
                "Dockerfile",
            ):
                continue
            try:
                total_bytes += path.stat().st_size
            except OSError:
                pass
            count += 1
    return count, total_bytes


def _size_tier(code_files: int) -> str:
    if code_files < 150:
        return "small"
    if code_files < 1500:
        return "medium"
    return "large"


def _wiki_state(workspace: Path, wiki_root: str) -> dict:
    wiki = workspace / wiki_root
    manifest = workspace / "sources" / "manifest.json"
    entities = wiki / "entities"
    entity_count = 0
    if entities.is_dir():
        entity_count = sum(1 for p in entities.glob("*.md") if p.is_file())
    last_ingest = None
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            last_ingest = data.get("last_ingest_commit")
        except (json.JSONDecodeError, OSError):
            pass
    head = "none"
    git_dir = workspace / ".git"
    if git_dir.exists():
        import subprocess

        try:
            head = (
                subprocess.check_output(
                    ["git", "-C", str(workspace), "rev-parse", "HEAD"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                .strip()[:7]
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return {
        "wiki_exists": wiki.is_dir(),
        "entity_count": entity_count,
        "last_ingest_commit": last_ingest,
        "head_short": head,
        "ingest_current": last_ingest is not None and last_ingest.startswith(head),
    }


def _wiki_action(
    repo_profile: str,
    size_tier: str,
    wiki_cfg: dict,
    wiki_state: dict,
) -> tuple[str, str]:
    """Return (action, reason). action: skip | init | ingest."""
    if not wiki_cfg.get("enabled", True):
        return "skip", "project_wiki.enabled is false"
    if repo_profile == "greenfield":
        return "skip", "greenfield — no codebase to compile"
    if not wiki_cfg.get("auto", True):
        return "skip", "project_wiki.auto is false"

    threshold = wiki_cfg.get("ingest_on", "medium")
    tier_rank = {"small": 0, "medium": 1, "large": 2}
    needs_wiki = tier_rank[size_tier] >= tier_rank.get(threshold, 1)

    if not needs_wiki and size_tier == "small":
        return "skip", f"brownfield {size_tier} — below ingest threshold ({threshold})"

    if wiki_state["ingest_current"] and wiki_state["entity_count"] > 0:
        return "skip", "wiki ingested at current HEAD with entities"

    if not wiki_state["wiki_exists"]:
        if needs_wiki or size_tier != "small":
            return "init", "brownfield — scaffold team wiki"
        return "skip", f"brownfield {size_tier} — wiki optional"

    if wiki_state["entity_count"] == 0 or not wiki_state["ingest_current"]:
        if tier_rank[size_tier] >= tier_rank.get(threshold, 1):
            return "ingest", f"brownfield {size_tier} — run ingest (entities missing or stale)"
        return "init", "wiki exists — entities empty; init only"

    return "skip", "wiki ready"


def profile_repo(workspace: Path) -> dict:
    workspace = workspace.resolve()
    code_files, code_bytes = _scan_code_files(workspace)
    repo_profile = check_repo_profile(str(workspace))
    # Prefer file scan for profile when check_repo_profile uses broader walk
    if code_files == 0:
        repo_profile = "greenfield"
    elif repo_profile == "greenfield" and code_files > 0:
        repo_profile = "brownfield"

    size_tier = _size_tier(code_files)
    stack = detect_stack(str(workspace))
    wiki_cfg = _load_project_wiki_config(workspace)
    wiki_root = wiki_cfg.get("root", "wiki")
    wiki_state = _wiki_state(workspace, wiki_root)
    action, reason = _wiki_action(repo_profile, size_tier, wiki_cfg, wiki_state)

    return {
        "workspace": str(workspace),
        "repo_profile": repo_profile,
        "repo_size": size_tier,
        "metrics": {
            "code_files": code_files,
            "code_bytes": code_bytes,
        },
        "detected_stack": stack,
        "wiki": {
            "action": action,
            "reason": reason,
            "config": wiki_cfg,
            "state": wiki_state,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile consumer repo for ADLC5")
    parser.add_argument("--workspace", default=".", help="Consumer project root")
    parser.add_argument(
        "--field",
        default="",
        help="Print single field only (repo_profile, repo_size, wiki.action, …)",
    )
    args = parser.parse_args()
    result = profile_repo(Path(args.workspace))

    if args.field:
        keys = args.field.split(".")
        val: object = result
        for key in keys:
            if isinstance(val, dict) and key in val:
                val = val[key]
            else:
                print("", end="")
                return 1
        print(val if not isinstance(val, (dict, list)) else json.dumps(val))
        return 0

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
