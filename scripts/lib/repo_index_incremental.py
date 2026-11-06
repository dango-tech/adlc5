"""Minimal incremental repo-index manifest helper.

Tracks hashes of source files under root and reports which changed since the
last stored manifest (.agent-cache/index-manifest.json).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

TRACKED_SUFFIXES = {".py", ".js", ".ts", ".go", ".rs", ".java", ".md"}
EXCLUDED = {".git", ".agent-cache", "node_modules", "__pycache__", "dist", "build"}


def _tracked_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDED for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() in TRACKED_SUFFIXES:
            yield p.relative_to(root)


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_manifest(root: Path) -> dict:
    root = Path(root)
    files = {}
    for rel in _tracked_files(root):
        files[rel.as_posix()] = _hash(root / rel)
    return {"files": files}


def changed_files(root: Path, manifest: dict) -> list[str]:
    root = Path(root)
    old = (manifest or {}).get("files", {})
    changed = []
    for rel in _tracked_files(root):
        key = rel.as_posix()
        new_hash = _hash(root / rel)
        if old.get(key) != new_hash:
            changed.append(key)
    # removed files also count as changed
    for key in old:
        if not (root / key).is_file():
            changed.append(key)
    return sorted(set(changed))


def update_manifest(root: Path, manifest: dict | None = None) -> dict:
    root = Path(root)
    new = build_manifest(root)
    if manifest is not None:
        # merge: keep old entries for files still present
        pass
    cache = root / ".agent-cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "index-manifest.json").write_text(
        json.dumps(new, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return new


def load_manifest(root: Path) -> dict:
    p = Path(root) / ".agent-cache" / "index-manifest.json"
    if not p.is_file():
        return {"files": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("print(1)\n", encoding="utf-8")
        (root / "b.md").write_text("hi\n", encoding="utf-8")
        m = build_manifest(root)
        assert m["files"]
        update_manifest(root, m)
        m2 = load_manifest(root)
        assert changed_files(root, m2) == [], changed_files(root, m2)
        # modify
        (root / "a.py").write_text("print(2)\n", encoding="utf-8")
        assert changed_files(root, m2) == ["a.py"]
        print("self-check ok")


if __name__ == "__main__":
    main()
