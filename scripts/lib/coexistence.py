"""Detect classic-install artifacts that duplicate the ADLC5 plugin (report only, never delete)."""
from __future__ import annotations

import json
from pathlib import Path

HOOK_MARKERS = ("claude-usage.sh", "engagement-gate.sh")


def _hook_commands(settings: Path) -> bool:
    try:
        text = settings.read_text(encoding="utf-8")
        json.loads(text)
    except (OSError, json.JSONDecodeError):
        return False
    return any(marker in text for marker in HOOK_MARKERS)


def _adlc5_skill_entries(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir() if p.name.startswith("adlc5"))


def find_duplicates(project: Path, home: Path | None = None) -> list[dict[str, str]]:
    """Classic artifacts that would run next to the plugin. Each item: kind, path, message."""
    home = home or Path.home()
    found: list[dict[str, str]] = []

    for settings in (
        project / ".claude" / "settings.json",
        project / ".claude" / "settings.local.json",
        home / ".claude" / "settings.json",
    ):
        if settings.is_file() and _hook_commands(settings):
            found.append({
                "kind": "hooks",
                "path": str(settings),
                "message": "classic ADLC5 usage/engagement hooks also run next to the plugin hooks "
                           "(duplicate warnings, repeated usage scans); remove them from this settings file",
            })

    for skills in (home / ".claude" / "skills", project / ".claude" / "skills", project / ".agents" / "skills"):
        names = _adlc5_skill_entries(skills)
        if names:
            found.append({
                "kind": "skills",
                "path": str(skills),
                "message": f"classic ADLC5 skill links ({len(names)}, e.g. {names[0]}) duplicate the plugin's skills; "
                           "keep one source (remove with ./scripts/cleanup-stale-skills.sh or delete the links)",
            })

    project_mcp = project / ".mcp.json"
    if project_mcp.is_file() and "adlc5-mcp" in project_mcp.read_text(encoding="utf-8", errors="replace"):
        found.append({
            "kind": "mcp",
            "path": str(project_mcp),
            "message": "project .mcp.json also declares an ADLC5 MCP server; the plugin already provides one",
        })
    return found
