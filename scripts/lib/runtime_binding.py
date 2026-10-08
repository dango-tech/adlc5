"""Stale ADLC5 runtime-binding detection/repair (see scripts/rebind-runtime.py)."""
from __future__ import annotations

import json
import re
from pathlib import Path

YAML_LINE = re.compile(r"^(adlc5_root:\s*)(.*?)(\s*(?:#.*)?)$")


def is_adlc5_root(path: str) -> bool:
    return bool(path) and (Path(path) / "scripts" / "adlc5").is_file() and (Path(path) / "core" / "VERSION").is_file()


def is_stale(recorded: str, current: Path) -> bool:
    if not recorded or recorded == "/path/to/adlc5":
        return False  # unset/template placeholder: not an ADLC5-owned binding
    try:
        same = Path(recorded).resolve() == current.resolve()
    except OSError:
        same = False
    if same:
        return False
    # A recorded root that still exists is a valid hint, even if another host's package:
    # each host selects its own runtime, so hosts must not rebind over one another.
    return not is_adlc5_root(recorded)


def unquote(value: str) -> str:
    return value.strip().strip("'\"")


def rebind_json(path: Path, root: Path, dry_run: bool) -> dict:
    if not path.is_file():
        return {"file": str(path), "status": "absent"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"file": str(path), "status": "unreadable"}
    old = data.get("adlc5_root", "")
    if not isinstance(old, str) or not is_stale(old, root):
        return {"file": str(path), "status": "kept", "adlc5_root": old}
    version = (root / "core" / "VERSION").read_text(encoding="utf-8").strip()
    data["adlc5_root"], data["adlc5_version"] = str(root), version
    if not dry_run:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"file": str(path), "status": "would-rebind" if dry_run else "rebound", "from": old, "to": str(root)}


def rebind_yaml(path: Path, root: Path, dry_run: bool) -> dict:
    target = path.resolve()  # config.yaml may be a symlink into the shared worktree store
    if not target.is_file():
        return {"file": str(path), "status": "absent"}
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        match = YAML_LINE.match(line.rstrip("\r\n"))
        if not match:
            continue
        old = unquote(match.group(2))
        if not is_stale(old, root):
            return {"file": str(target), "status": "kept", "adlc5_root": old}
        ending = line[len(line.rstrip("\r\n")):]
        lines[i] = f"{match.group(1)}{root}{match.group(3)}{ending}"
        if not dry_run:
            target.write_text("".join(lines), encoding="utf-8")
        return {"file": str(target), "status": "would-rebind" if dry_run else "rebound", "from": old, "to": str(root)}
    return {"file": str(target), "status": "kept", "adlc5_root": None}




def binding_state(workspace: Path, root: Path) -> str | None:
    """One-line notice when the consumer's recorded adlc5_root is stale for `root`, else None."""
    cfg = workspace / ".adlc5" / "workspace.json"
    if not cfg.is_file():
        return None
    try:
        old = json.loads(cfg.read_text(encoding="utf-8")).get("adlc5_root", "")
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(old, str) and is_stale(old, root):
        return (f"Workspace binding .adlc5/workspace.json records adlc5_root={old}, which is stale; "
                "hooks/MCP/bin use this plugin's runtime regardless. adlc5-setup refreshes the record.")
    return None
