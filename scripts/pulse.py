#!/usr/bin/env python3
"""ADLC5 Pulse: on-demand snapshot, terminal band, offline board, and handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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


def _cache_dir(workspace: Path, parts=(".adlc5", "pulse")) -> Path:
    root = workspace.resolve(strict=True)
    current = root
    for part in parts:
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
        if hasattr(os, 'fchmod'):
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
    directory = Path.home() / '.adlc5/pulse/workspaces' / _cache_key(str(workspace.resolve()))
    try:
        for pathpart in (Path.home() / '.adlc5', directory.parent.parent, directory.parent, directory):
            info = pathpart.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                return {}
        matches = []
        candidates = sorted(directory.glob("feature-*.json"))
        if len(candidates) > 200:
            return {}
        reader = Reader(Path.home())
        for path in candidates:
            raw = reader.read(path)
            if raw is None:
                continue
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("schema_version") == "1.0" and any(not feature or feature in (row.get("id"), row.get("archive_id")) for row in data.get("features", []) if isinstance(row, dict)):
                matches.append(data)
        return matches[0] if len(matches) == 1 else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _board_sessions(workspace):
    """Sessions in this worktree's project from the last all-projects board (~/.adlc5/pulse/fleet.json), each
    tagged local=True when it ran in this worktree; [] if the cache is absent or unreadable."""
    from lib.pulse_fleet import workspace_key
    home = Path.home()
    try:
        raw = Reader(home).read(home / '.adlc5/pulse/fleet.json')
        fleet = json.loads(raw).get('fleet', {}) if raw else {}
        sessions, inventory = fleet.get('sessions', []), fleet.get('workspace_inventory', [])
    except (OSError, ValueError, AttributeError):  # the band must never fail over a missing or stale cache
        return []
    key = workspace_key(workspace)
    project = next((w.get('project_id') for w in inventory if isinstance(w, dict) and w.get('key') == key), None)
    keys = {w.get('key') for w in inventory if isinstance(w, dict) and project and w.get('project_id') == project} | {key}
    return [{**s, 'local': key in s['workspace_keys']} for s in sessions
            if isinstance(s, dict) and isinstance(s.get('workspace_keys'), list) and keys & set(s['workspace_keys'])]


def _fleet_board(args, workspace=None, snapshot=None):
    from lib.pulse_fleet import collect, workspace_key, workspace_label
    home = Path.home()
    cache = _cache_dir(home)
    sources = cache / 'roots.json'
    # Retain roots from the first global-board implementation without moving old files.
    legacy = home / '.config/adlc5/pulse/roots.json'
    reader = Reader(home)
    existing = []
    for source in (sources, legacy):
        raw = reader.read(source)
        if raw is not None:
            values = json.loads(raw)
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise ValueError('invalid local Pulse root registry')
            existing.extend(values)
    defaults = [home / 'SourceCode/Github', home / '.codex/worktrees', home / 'Documents/Codex']
    roots = sorted({path.expanduser().resolve() for path in [*defaults, *map(Path, existing), *map(Path, args.root), *([workspace] if workspace else [])]})
    if workspace and snapshot is not None:
        directory = _cache_dir(home, ('.adlc5', 'pulse', 'workspaces', _cache_key(str(workspace))))
        for item in snapshot['features']:
            entry = {**snapshot, 'features': [item], 'capture': {**snapshot['capture'], 'scope': 'feature'}}
            _atomic_write(directory / f"feature-{item['identity']}.json", (json.dumps(entry) + '\n').encode())
        if args.host:
            _atomic_write(directory / f'host-{args.host}.json', json.dumps({
                'workspace_key': workspace_key(workspace), 'host': args.host,
                'workspace_label': workspace_label(workspace),
                'observed_at': snapshot['generated_at']}).encode())
    observations = []
    for path in (cache / 'workspaces').glob('*/host-*.json'):
        raw = reader.read(path)
        if raw is not None:
            observations.append(json.loads(raw))
    data = collect(roots, [('codex', home / '.codex/sessions'), ('codex', home / '.codex/archived_sessions'),
                          ('claude', home / '.claude/projects'), ('cursor', home / '.cursor/projects')],
                   active_only=args.active_only, observations=observations)
    from lib.pulse_settings import snapshot as settings_snapshot, integrations, shared_runtime
    settings = {'machine': settings_snapshot(None)}
    for row in data['fleet']['workspace_inventory']:
        path = Path(row['label']).expanduser()
        if path.is_dir():
            settings['worktree:' + row['key']] = settings_snapshot(path)
            settings.setdefault('project:' + row['project_id'], settings_snapshot(path, scope='project'))
    data['settings'] = {'scopes': settings, 'integrations': integrations(ROOT),
                        'shared_runtime': shared_runtime(),
                        'scan_roots': [str(path).replace(str(home), '~') for path in roots]}
    # Local-only board: lets "~/" labels become file:// links. Never added to shareable snapshots or handoffs.
    data['home_uri'] = home.as_uri()
    if workspace:
        key = workspace_key(workspace)
        selected = next((f['identity'] for f in data['features'] if f['workspace_key'] == key
                         and (not args.feature or args.feature in (f['id'], f.get('archive_id')))), None)
        data['selected_feature'] = selected
    _atomic_write(sources, (json.dumps([str(path) for path in roots], indent=2) + '\n').encode())
    _atomic_write(cache / 'fleet.json', (json.dumps(data, ensure_ascii=True, indent=2) + '\n').encode())
    path = cache / 'board.html'
    _atomic_write(path, board_document(data).encode())
    print(json.dumps({'status': data['status'], 'board': str(path), 'features': len(data['features']),
                      'sessions': len(data['fleet']['sessions']), 'attempts': len(data['fleet']['attempts']),
                      'captured_at': data['generated_at']}))
    if args.open_board:
        webbrowser.open(path.as_uri())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "band", "board", "handoff"))
    parser.add_argument("--workspace")
    parser.add_argument("--feature")
    parser.add_argument("--archive-id")
    parser.add_argument("--active-only", action="store_true")
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--open", action="store_true", dest="open_board")
    parser.add_argument("--all-projects", action="store_true", help="Write the global local board, including native session inventory")
    parser.add_argument("--root", action="append", default=[], help="Additional scan root for --all-projects; remembered locally")
    parser.add_argument('--host', choices=('claude', 'codex', 'cursor', 'hermes'), help='Record the calling host for this workspace')
    args = parser.parse_args(argv)
    if args.host and (args.action != 'board' or args.all_projects):
        parser.error('--host requires board with a workspace')
    if args.all_projects:
        if args.action != 'board' or args.feature or args.archive_id or args.workspace or args.cached:
            parser.error('--all-projects is a board operation; use --root instead of workspace/feature selection')
        try:
            return _fleet_board(args)
        except (OSError, ValueError) as exc:
            print(json.dumps({'status': 'error', 'error': str(exc)}), file=sys.stderr)
            return 2
    if args.root:
        parser.error('--root requires --all-projects')
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
            line = band(data, args.feature, _board_sessions(workspace))
            print(line + " · present freshness unverified")
            return 0
        data = project_workspace(workspace, args.feature, args.active_only)
        if args.action == "snapshot":
            print(json.dumps(data, ensure_ascii=True, indent=2))
            return 0
        if args.action == "band":
            print(band(data, args.feature, _board_sessions(workspace)))
            return 0
        if args.action == "handoff":
            if not args.feature:
                parser.error("handoff requires --feature")
            print(handoff(data, args.feature), end="")
            return 0
        if args.action == "board":
            return _fleet_board(args, workspace, data)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
