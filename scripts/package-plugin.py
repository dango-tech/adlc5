#!/usr/bin/env python3
"""Build self-contained ADLC5 packages for Codex, Claude Code, Cursor and Hermes.

  scripts/package-plugin.py [--out DIR] [--host all|codex|claude|cursor] [--check]

Writes a host-specific directory and zip for each selected host (default DIR:
<tmp>/adlc5-dist, never inside the source tree). Codex and Claude outputs also include local
marketplace roots so developers can register and install the packages using each host's native
workflow. Cursor's output is a local plugin directory suitable for ~/.cursor/plugins/local.

Safety model:
  * candidates come from `git ls-files --cached --others --exclude-standard`, so ignored files
    (.adlc5, .agents, caches, config.yaml, .env*, backups, credentials) are never read;
  * an allowlist keeps only runtime, skill-reference and host-package paths;
  * symlinks are refused (a package may not depend on anything outside itself);
  * a secret / personal-path scan fails the build, printing paths only;
  * `.adlc5-package.json` marks the tree immutable: kernel/MCP/init refuse consumer
    workspaces inside it.

Determinism: sorted entries, fixed mtime, root:root, normalized modes (0755 if executable else 0644),
gzip mtime 0. Same source revision and working-tree state → byte-identical archives.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
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
    "core/", "skills/", "scripts/", "shared/", "templates/", "docs/", "assets/brand/",
    "config.example.yaml", "LICENSE", "README.md", "CHANGELOG.md",
)
EXCLUDE_PREFIXES = (
    "scripts/tests/", "docs/plans/", "docs/adr/", "dogfood/", "platform/runner/", ".agents/",
)
EXCLUDE_NAMES = {"__pycache__", ".DS_Store"}
EXCLUDE_SUFFIXES = (".pyc", ".swp", ".bak", ".orig", ".log")
REQUIRED_BASE = (
    "core/VERSION", "core/gates.yaml", "skills/adlc5/SKILL.md", "skills/adlc5-setup/SKILL.md",
    "scripts/adlc5", "scripts/adlc5-mcp.py", "scripts/init-workspace.sh", "scripts/plugin-setup.sh",
    "scripts/lib/requirements_readiness.py", "docs/requirements-readiness.md",
    "scripts/runner/questions.py", "core/guides/profile-routing.md",
    "scripts/install-plugin.py",
    "core/pulse-snapshot.schema.json", "scripts/pulse.py", "scripts/pulse-statusline.py",
    "scripts/lib/pulse.py", "scripts/lib/pulse_fleet.py", "scripts/lib/pulse_settings.py", "scripts/shared-home.py", "scripts/lib/config_layers.py", "skills/pulse/SKILL.md", "shared/pulse/board.html",
    "shared/pulse/board.css", "shared/pulse/board.js", "assets/brand/icon.svg",
    "LICENSE",
)
REQUIRED_BY_HOST = {
    "claude": (
    ".claude-plugin/plugin.json", ".mcp.json", "hooks/claude.json", "bin/adlc5", "bin/adlc5-run",
    "hooks/pulse-band.json", "hooks/pulse-band.tsx",
    ".claude/hooks/claude-usage.sh", ".claude/hooks/engagement-gate.sh", "LICENSE",
    ),
    "codex": ("plugin.json", ".codex-plugin/plugin.json", "mcp.json", ".mcp.json"),
    "cursor": (".cursor-plugin/plugin.json", ".cursor-plugin/mcp.json", ".cursor-plugin/run-mcp.sh"),
    "hermes": ("plugin.json", "mcp.json"),
}

HOST_ONLY_PREFIXES = {
    # Keep repository marketplace metadata outside the distributable Claude plugin.
    # The builder emits a Claude-only marketplace catalog as a sibling directory.
    "claude": (".claude-plugin/marketplace.json", ".codex-plugin/", ".cursor-plugin/", "platform/codex-plugin/", "mcp.json"),
    "codex": (".claude-plugin/", ".claude/", ".cursor-plugin/", "hooks/claude.json", "hooks/pulse-band.", "bin/", "platform/codex-plugin/"),
    "cursor": (".claude-plugin/", ".claude/", ".codex-plugin/", "hooks/", ".mcp.json", "bin/", "platform/codex-plugin/", "mcp.json"),
    "hermes": (".claude-plugin/", ".claude/", ".codex-plugin/", ".codex/", ".cursor-plugin/", "hooks/", ".mcp.json", "bin/", "platform/codex-plugin/"),
}

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


def collect(root: Path, host: str) -> dict[str, tuple[bytes, int]]:
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
    missing = [r for r in (*REQUIRED_BASE, *REQUIRED_BY_HOST[host]) if r not in files]
    problems += [f"required file missing from package: {m}" for m in missing]
    if problems:
        raise SystemExit("package refused:\n  " + "\n  ".join(problems))
    version = files["core/VERSION"][0].decode().strip()
    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json", ".cursor-plugin/plugin.json", "platform/codex-plugin/plugin.json"):
        if manifest in files and json.loads(files[manifest][0]).get("version") != version:
            raise SystemExit(f"{manifest} version differs from core/VERSION {version!r}")
    registry = files.get("core/skill-registry.yaml")
    if registry and f'framework_version: "{version}"' not in registry[0].decode():
        raise SystemExit(f"core/skill-registry.yaml version differs from core/VERSION {version!r}")
    files[".adlc5-package.json"] = (build_manifest(version), 0o644)
    return dict(sorted(files.items()))


def for_host(files: dict[str, tuple[bytes, int]], host: str, version: str) -> dict[str, tuple[bytes, int]]:
    omitted = HOST_ONLY_PREFIXES[host]
    result = {
        name: value for name, value in files.items()
        if not any(name == prefix or name.startswith(prefix) for prefix in omitted)
    }
    if host == "codex":
        # Root plugin.json is the portable Agent Plugins entry point; retain
        # .codex-plugin/plugin.json as the documented compatibility fallback.
        manifest = json.loads(result["plugin.json"][0])
        manifest["version"] = version
        manifest.setdefault("extensions", {}).setdefault("com.openai", {})["interface"] = {
            "displayName": "ADLC5",
            "shortDescription": "Evidence-driven software delivery for coding agents.",
            "longDescription": "Specify, plan, implement, and verify software changes with shared skills and a local deterministic kernel.",
            "developerName": "Dango Tech",
            "category": "Developer tools",
            "capabilities": ["Plan and implement software changes", "Run deterministic workflow checks"],
        }
        result["plugin.json"] = (json.dumps(manifest, indent=2).encode() + b"\n", 0o644)
        compatibility = {
            "name": "adlc5",
            "version": version,
            "description": "ADLC5 workflow skills and local kernel tools for Codex.",
            "author": {"name": "Dango Tech", "url": "https://github.com/dango-tech"},
            "skills": "./skills/",
            "mcpServers": "./.mcp.json",
            "interface": {
                "displayName": "ADLC5",
                "shortDescription": "Evidence-driven software delivery for coding agents.",
                "longDescription": "Specify, plan, implement, and verify software changes with shared skills and a local deterministic kernel.",
                "developerName": "Dango Tech",
                "category": "Developer tools",
                "capabilities": ["Plan and implement software changes", "Run deterministic workflow checks"],
            },
        }
        result[".codex-plugin/plugin.json"] = (json.dumps(compatibility, indent=2).encode() + b"\n", 0o644)
        mcp = {
            "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": {
                "adlc5": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["./scripts/adlc5-mcp.py"],
                    "cwd": "${PLUGIN_ROOT}",
                }
            },
        }
        result["mcp.json"] = (json.dumps(mcp, indent=2).encode() + b"\n", 0o644)
        compatibility_mcp = {
            "mcpServers": {
                "adlc5": {
                    "command": "python3",
                    "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/adlc5-mcp.py"],
                }
            }
        }
        result[".mcp.json"] = (json.dumps(compatibility_mcp, indent=2).encode() + b"\n", 0o644)
    result[".adlc5-package.json"] = (build_manifest(version), 0o644)
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=normal'], text=True))
    result['INSTALL.json'] = (json.dumps({'host': host, 'version': version, 'source_revision': revision, 'source_dirty': dirty}, sort_keys=True).encode() + b'\n', 0o644)
    result['install.py'] = (b'from pathlib import Path\nimport runpy\nrunpy.run_path(str(Path(__file__).parent / "scripts/install-plugin.py"), run_name="__main__")\n', 0o644)
    return dict(sorted(result.items()))


def write_marketplace(root: Path, host: str, package_dir: Path) -> None:
    """Create an installable local marketplace for Codex or Claude Code."""
    plugins = root / "plugins"
    plugins.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package_dir, plugins / "adlc5")
    if host == "codex":
        marketplace = {
            "name": "adlc5-local",
            "interface": {"displayName": "ADLC5 local build"},
            "plugins": [{
                "name": "adlc5",
                "source": {"source": "local", "path": "./plugins/adlc5"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Developer tools",
            }],
        }
        path = root / ".agents" / "plugins" / "marketplace.json"
    else:
        marketplace = {
            "name": "adlc5-local",
            "description": "Local ADLC5 plugin build",
            "owner": {"name": "ADLC5"},
            "plugins": [{"name": "adlc5", "source": "./plugins/adlc5", "description": "ADLC5 workflow skills and kernel tools"}],
        }
        path = root / ".claude-plugin" / "marketplace.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marketplace, indent=2) + "\n", encoding="utf-8")


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
    parser.add_argument("--host", choices=("all", "codex", "claude", "cursor", "hermes"), default="all")
    parser.add_argument("--check", action="store_true", help="validate host package inputs only; write nothing")
    parser.add_argument("--claude-hosted", action="store_true", help="omit PATH executables for Claude Desktop upload/directory validation")
    ns = parser.parse_args()
    if ns.claude_hosted and ns.host != "claude":
        parser.error("--claude-hosted requires --host claude")
    hosts = ("codex", "claude", "cursor", "hermes") if ns.host == "all" else (ns.host,)
    files_by_host = {host: for_host(collect(ROOT, host), host, (ROOT / "core/VERSION").read_text(encoding="utf-8").strip()) for host in hosts}
    if ns.claude_hosted:
        files_by_host["claude"] = {name: value for name, value in files_by_host["claude"].items() if not name.startswith("bin/")}
    version = (ROOT / "core/VERSION").read_text(encoding="utf-8").strip()
    if ns.check:
        print(json.dumps({"status": "ok", "version": version, "hosts": {host: len(files) for host, files in files_by_host.items()}}))
        return 0
    out = Path(ns.out).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"--out must be outside the source tree: {out}")
    out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for host, files in files_by_host.items():
        label = "claude-code" if host == "claude" else host
        package_dir = out / host / "adlc5"
        shutil.rmtree(out / host, ignore_errors=True)
        marketplace_root = out / f"{host}-marketplace"
        shutil.rmtree(marketplace_root, ignore_errors=True)
        for archive in out.glob(f"adlc5-{label}-plugin-*"):
            archive.unlink()
        if host == "claude":
            for archive in out.glob("adlc5-plugin-*"):
                archive.unlink()
        package_dir.mkdir(parents=True)
        for name, (data, _mode) in files.items():
            dest = package_dir / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        for name, (_data, mode) in files.items():
            path = package_dir / name
            path.chmod(mode)
        zip_path = out / f"adlc5-{label}-plugin-{version}.zip"
        tar_path = out / f"adlc5-{label}-plugin-{version}.tar.gz"
        write_zip(files, zip_path)
        tar_prefix = f"adlc5-{version}" if host == "claude" else f"adlc5-{label}-{version}"
        write_tar(files, tar_path, tar_prefix)
        if host in ("codex", "claude"):
            write_marketplace(marketplace_root, host, package_dir)
            outputs[host] = {"directory": str(package_dir), "zip": str(zip_path), "tar": str(tar_path), "marketplace": str(marketplace_root)}
        else:
            outputs[host] = {"directory": str(package_dir), "zip": str(zip_path), "tar": str(tar_path)}
    result = {"status": "ok", "version": version, "packages": outputs}
    archives = sorted(Path(values[key]) for values in outputs.values() for key in ('zip', 'tar'))
    checksums = out / 'SHA256SUMS'
    checksums.write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n' for path in archives))
    result['checksums'] = str(checksums)
    if "claude" in outputs:
        # Retain the original Claude package keys for scripts that consumed the 4.x builder.
        result.update({"files": len(files_by_host["claude"]), "tar": outputs["claude"]["tar"], "zip": outputs["claude"]["zip"]})
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
