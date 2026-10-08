#!/usr/bin/env python3
"""Build the deterministic, self-contained ADLC5 plugin archive (Claude Code; shared with Codex).

  scripts/package-plugin.py [--out DIR] [--check]

Writes DIR/adlc5-plugin-<version>.tar.gz and .zip (default DIR: <tmp>/adlc5-dist, never inside
the source tree). Both hold the same files under the package root (the zip loads directly with
`claude --plugin-dir <zip>`). One package serves every host: Claude, Codex and Cursor metadata
travel together when present.

Safety model:
  * candidates come from `git ls-files --cached --others --exclude-standard`, so ignored files
    (.adlc5, .agents, caches, config.yaml, .env*, backups, credentials) are never read;
  * an allowlist keeps only runtime, skill-reference and host-package paths;
  * symlinks are refused (a package may not depend on anything outside itself);
  * a secret / personal-path scan fails the build, printing paths only;
  * `.adlc5-package.json` marks the tree immutable: kernel/MCP/init refuse consumer
    workspaces inside it.

Determinism: sorted entries, fixed mtime, root:root, normalized modes (0755 if executable else 0644),
gzip mtime 0. Same tree → byte-identical archives.
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MTIME = 315532800  # 1980-01-01, the earliest zip timestamp

INCLUDE_PREFIXES = (
    ".claude-plugin/", ".claude/hooks/", ".codex-plugin/", ".codex/hooks/", ".cursor/rules/", ".cursor-plugin/",
    ".mcp.json", "mcp.json", "plugin.json", "bin/", "hooks/", "platform/",
    "core/", "skills/", "scripts/", "shared/", "templates/", "docs/",
    "config.example.yaml", "LICENSE", "README.md", "CHANGELOG.md",
)
EXCLUDE_PREFIXES = (
    "scripts/tests/", "docs/plans/", "docs/adr/", "dogfood/", "platform/runner/",
)
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}
EXCLUDE_SUFFIXES = (".pyc", ".swp", ".bak", ".orig", ".log")
REQUIRED = (
    ".claude-plugin/plugin.json", ".mcp.json", "hooks/claude.json", "bin/adlc5", "bin/adlc5-run",
    "scripts/adlc5", "scripts/adlc5-mcp.py", "scripts/init-workspace.sh", "scripts/plugin-setup.sh",
    "core/VERSION", "core/gates.yaml", "skills/adlc5/SKILL.md", "skills/adlc5-setup/SKILL.md",
    ".claude/hooks/claude-usage.sh", ".claude/hooks/engagement-gate.sh", "LICENSE",
)

SECRET = re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_\-]{30,}|\bAKIA[A-Z0-9]{16}\b")
HOME = re.compile(rb"/(?:Users|home)/(?!USER\b|username\b|user\b|you\b|example\b|test\b)[A-Za-z][A-Za-z0-9_-]+/")


def candidates(root: Path) -> list[str]:
    out = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    ).decode()
    return sorted({n for n in out.split("\0") if n})


def selected(names: list[str], root: Path) -> list[str]:
    keep = []
    for name in names:
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue  # deleted in the worktree but still in the index
        parts = Path(name).parts
        if any(p in EXCLUDE_NAMES for p in parts) or name.endswith(EXCLUDE_SUFFIXES):
            continue
        if name.startswith(EXCLUDE_PREFIXES) or not name.startswith(INCLUDE_PREFIXES):
            continue
        keep.append(name)
    return keep


def build_manifest(version: str) -> bytes:
    data = {
        "name": "adlc5",
        "version": version,
        "kind": "installed-package",
        "note": "Immutable package. Consumer state lives in the consumer repository's .adlc5/.",
    }
    return (json.dumps(data, indent=2) + "\n").encode()


def collect(root: Path) -> dict[str, tuple[bytes, int]]:
    files: dict[str, tuple[bytes, int]] = {}
    problems: list[str] = []
    for name in selected(candidates(root), root):
        path = root / name
        if path.is_symlink():
            problems.append(f"symlink not allowed in package: {name}")
            continue
        if not path.is_file():
            continue
        data = path.read_bytes()
        if SECRET.search(data.replace(b"AKIAIOSFODNN7EXAMPLE", b"AWS_DOCUMENTATION_EXAMPLE")):
            problems.append(f"possible credential: {name}")
        if HOME.search(data):
            problems.append(f"personal filesystem path: {name}")
        mode = 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644
        files[name] = (data, mode)
    missing = [r for r in REQUIRED if r not in files]
    problems += [f"required file missing from package: {m}" for m in missing]
    if problems:
        raise SystemExit("package refused:\n  " + "\n  ".join(problems))
    version = files["core/VERSION"][0].decode().strip()
    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json", ".cursor-plugin/plugin.json"):
        if manifest in files and json.loads(files[manifest][0]).get("version") != version:
            raise SystemExit(f"{manifest} version differs from core/VERSION {version!r}")
    files[".adlc5-package.json"] = (build_manifest(version), 0o644)
    return dict(sorted(files.items()))


def write_tar(files: dict[str, tuple[bytes, int]], dest: Path, prefix: str) -> None:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, (data, mode) in files.items():
            info = tarfile.TarInfo(f"{prefix}/{name}")
            info.size, info.mode, info.mtime = len(data), mode, MTIME
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    with open(dest, "wb") as handle, gzip.GzipFile(fileobj=handle, mode="wb", mtime=0, filename="") as gz:
        gz.write(raw.getvalue())


def write_zip(files: dict[str, tuple[bytes, int]], dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, (data, mode) in files.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "adlc5-dist"))
    parser.add_argument("--check", action="store_true", help="validate the file selection only; write nothing")
    ns = parser.parse_args()
    files = collect(ROOT)
    version = files["core/VERSION"][0].decode().strip()
    if ns.check:
        print(json.dumps({"status": "ok", "version": version, "files": len(files)}))
        return 0
    out = Path(ns.out).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"--out must be outside the source tree: {out}")
    out.mkdir(parents=True, exist_ok=True)
    tar_path, zip_path = out / f"adlc5-plugin-{version}.tar.gz", out / f"adlc5-plugin-{version}.zip"
    write_tar(files, tar_path, f"adlc5-{version}")
    write_zip(files, zip_path)
    print(json.dumps({"status": "ok", "version": version, "files": len(files), "tar": str(tar_path), "zip": str(zip_path)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
