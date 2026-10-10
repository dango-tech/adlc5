"""Paths and small helpers for ADLC5's machine and repository config layers."""
from __future__ import annotations

import subprocess
from pathlib import Path


def config_paths(workspace: Path | None) -> list[tuple[str, Path]]:
    paths = [("master", Path.home() / ".adlc5" / "config.yaml")]
    if workspace is None:
        return paths
    workspace = workspace.resolve()
    legacy = workspace / ".adlc5" / "config.yaml"
    proc = subprocess.run(["git", "-C", str(workspace), "rev-parse", "--git-common-dir"],
                          capture_output=True, text=True, check=False)
    if proc.returncode == 0:
        common = Path(proc.stdout.strip())
        if not common.is_absolute():
            common = (workspace / common).resolve()
        if legacy.is_file() and not legacy.is_symlink():
            paths.append(("legacy_repo", legacy))
        shared = common / "adlc5-shared" / "config.yaml"
        if shared.is_file():
            paths.append(("repo", shared))
        elif legacy.exists():
            paths.append(("legacy_repo", legacy))
    else:
        paths.append(("repo", workspace / ".adlc5" / "config.yaml"))
    return paths


def merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out
