"""Refuse consumer writes into an installed (immutable) ADLC5 package.

A packaged distribution (for example the Claude Code plugin cache) carries a
`.adlc5-package.json` marker written by `scripts/package-plugin.py`. A source
clone has no marker, so framework development and `dogfood/` runs are unaffected.
"""
from __future__ import annotations

import os
from pathlib import Path

MARKER = ".adlc5-package.json"


def is_installed_package(root: Path) -> bool:
    return (Path(root) / MARKER).is_file()


def resolve_workspace(value: str | os.PathLike[str] | None, base: Path | None = None) -> Path:
    """Absolute workspace path; relative values resolve against `base` (default cwd)."""
    path = Path(value) if value not in (None, "") else Path(".")
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    return path.resolve()


def check_workspace(root: Path, workspace: Path) -> str | None:
    """Return an error message when `workspace` is unusable, else None."""
    if not workspace.is_dir():
        return f"workspace is not a directory: {workspace}"
    root = Path(root).resolve()
    if is_installed_package(root) and (workspace == root or root in workspace.parents):
        return (
            f"workspace {workspace} is inside the installed ADLC5 package {root}; "
            "pass --workspace <consumer repository> (package contents are immutable)"
        )
    return None
