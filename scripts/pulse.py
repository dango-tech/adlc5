#!/usr/bin/env python3
"""ADLC5 Pulse: on-demand snapshot, terminal band, offline board, and handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
import sys
import tempfile
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from lib.package_guard import check_workspace, resolve_workspace  # noqa: E402
from lib.pulse import Reader, band, board_document, handoff, project_workspace  # noqa: E402


def _cache_dir(workspace: Path) -> Path:
    root = workspace.resolve(strict=True)
    current = root
    for part in (".agent-cache", "pulse"):
        current = current / part
        try:
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ValueError("Pulse cache path is unsafe")
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            current.chmod(0o700)
    return current


def _atomic_write(path: Path, content: bytes) -> None:
    directory = path.parent
    fd, temp_name = tempfile.mkstemp(prefix=".pulse-", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _cache_key(feature: str | None) -> str:
    label = feature or "workspace"
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:20]


def _load_cache(workspace: Path, feature: str) -> dict:
    directory = workspace / ".agent-cache" / "pulse"
    try:
        for pathpart in (workspace / ".agent-cache", directory):
            info = pathpart.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                return {}
        matches = []
        candidates = sorted(directory.glob("feature-*.json"))
        if len(candidates) > 200:
            return {}
        reader = Reader(workspace)
        for path in candidates:
            raw = reader.read(path)
            if raw is None:
                continue
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("schema_version") == "1.0" and any(feature in (row.get("id"), row.get("archive_id")) for row in data.get("features", []) if isinstance(row, dict)):
                matches.append(data)
        return matches[0] if len(matches) == 1 else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "band", "board", "handoff"))
    parser.add_argument("--workspace")
    parser.add_argument("--feature")
    parser.add_argument("--archive-id")
    parser.add_argument("--active-only", action="store_true")
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--open", action="store_true", dest="open_board")
    args = parser.parse_args(argv)
    workspace = resolve_workspace(args.workspace)
    problem = check_workspace(ROOT, workspace)
    if problem:
        print(json.dumps({"status": "error", "error": problem}), file=sys.stderr)
        return 2
    if args.archive_id:
        if args.feature:
            parser.error("use --archive-id or --feature, not both")
        args.feature = args.archive_id
    try:
        if args.action == "band" and args.cached:
            if not args.feature:
                parser.error("--cached band requires --feature")
            data = _load_cache(workspace, args.feature)
            if not data:
                print("ADLC5 Pulse · cached snapshot unavailable")
                return 0
            line = band(data, args.feature)
            print(line + " · present freshness unverified")
            return 0
        data = project_workspace(workspace, args.feature, args.active_only)
        if args.action == "snapshot":
            print(json.dumps(data, ensure_ascii=True, indent=2))
            return 0
        if args.action == "band":
            print(band(data, args.feature))
            return 0
        if args.action == "handoff":
            if not args.feature:
                parser.error("handoff requires --feature")
            print(handoff(data, args.feature), end="")
            return 0
        if args.action == "board":
            cache = _cache_dir(workspace)
            selection = data.get("features", [])
            suffix = selection[0].get("identity") if args.feature and selection else _cache_key(None)
            key = f"feature-{suffix}" if args.feature else "workspace"
            generation = secrets.token_hex(12)
            data["generation_id"] = generation
            encoded = (json.dumps(data, ensure_ascii=True, indent=2) + "\n").encode()
            html_path = cache / f"{key}.html"
            json_path = cache / f"{key}.json"
            _atomic_write(json_path, encoded)
            for item in selection:
                entry = dict(data)
                entry["capture"] = {**data["capture"], "scope": "feature"}
                entry["features"] = [item]
                _atomic_write(cache / f"feature-{item['identity']}.json", (json.dumps(entry, ensure_ascii=True, indent=2) + "\n").encode())
            try:
                _atomic_write(html_path, board_document(data).encode("utf-8"))
            except Exception:
                # The cached snapshot is harmless but has no paired board generation.
                json_path.unlink(missing_ok=True)
                raise
            print(json.dumps({"status": data["status"], "generation_id": generation, "snapshot": str(json_path.relative_to(workspace)), "board": str(html_path.relative_to(workspace)), "captured_at": data["generated_at"]}))
            if args.open_board:
                try:
                    webbrowser.open(html_path.as_uri())
                except Exception as exc:
                    print(f"warning: browser could not be opened: {type(exc).__name__}", file=sys.stderr)
            return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
