"""Local cross-workspace Pulse inventory; never execute consumer code or export prompts."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re

from lib.pulse import Reader, _json, _jsonl, _safe_text, project_workspace
from lib.config_layers import project_identity

PRUNE = {'.git', '.agent-cache', 'node_modules', '.venv', 'venv', '__pycache__',
         'Pods', '.build', 'DerivedData', 'dist', 'build', '.next', '.terraform'}
KERNEL = re.compile(r'(?:scripts/adlc5|\badlc5)\s+(?:transition|gate|pilot|evidence|state|anchors|readiness|run)\b|(?:init-feature\.sh|pilot-autopilot\.sh)')
FEATURE_ARG = re.compile(r'--feature[= ]+([A-Za-z0-9][A-Za-z0-9_.-]{0,80})|"feature"\s*:\s*"([A-Za-z0-9][A-Za-z0-9_.-]{0,80})"')
KERNEL_VERB = re.compile(r'(?:scripts/adlc5|\badlc5)\s+(transition|gate|pilot|evidence|state|anchors|readiness|run|pulse)\b')
REQUEST = re.compile(r'(?:@|\$|/)adlc5(?:[:\s-]|$)|\b(?:using|use|run|invoke|follow)\s+(?:the\s+)?adlc5\b', re.I)


def workspace_key(workspace: Path) -> str:
    return hashlib.sha256(str(workspace.resolve()).encode()).hexdigest()[:10]


def workspace_label(workspace: Path) -> str:
    try:
        return '~/' + workspace.resolve().relative_to(Path.home()).as_posix()
    except ValueError:
        return _safe_text(str(workspace.resolve()), 400)


def discover(roots: list[Path], warnings: list[str]) -> list[Path]:
    found = set()
    visited = set()
    for root in roots:
        if not root.is_dir():
            warnings.append('scan_root_unavailable: ' + root.name)
            continue
        for directory, names, _ in os.walk(root, followlinks=False, onerror=lambda _: warnings.append('directory_unreadable')):
            current = Path(directory).resolve()
            if current in visited:
                names[:] = []
                continue
            visited.add(current)
            if '.adlc5' in names or any((current / '.agent-cache/pulse' / name).is_file() for name in ('workspace.json', 'workspace.html')):
                found.add(current)
            names[:] = [name for name in names if name not in PRUNE and name != '.adlc5'
                        and not (current / name).is_symlink()]
    return sorted(found)


def content(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(str(part.get('text', '')) for part in value if isinstance(part, dict))
    return ''


def sessions(roots: list[tuple[str, Path]], warnings: list[str]) -> tuple[list[dict], int]:
    """Index explicit invocations, not incidental skill catalogs or assistant claims."""
    rows = {}
    counters = {}
    files = 0
    for host, root in roots:
        if host == 'codex':
            # Codex keeps generated thread names beside its session folders.
            for line in (root.parent / 'session_index.jsonl').read_text(encoding='utf-8', errors='replace').splitlines() if (root.parent / 'session_index.jsonl').is_file() else []:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and entry.get('id') and entry.get('thread_name'):
                    counters.setdefault('codex:' + str(entry['id']), {'messages': {}, 'snapshot': None})['title'] = _safe_text(entry['thread_name'], 160)
        for path in sorted(root.rglob('*.jsonl')) if root.is_dir() else []:
            if path.is_symlink() or not path.is_file():
                continue
            files += 1
            if files > 10000:
                warnings.append('session_file_limit_reached')
                return list(rows.values()), files - 1
            sid, cwd = path.stem, 'project unavailable'
            try:
                with path.open(encoding='utf-8', errors='replace') as stream:
                    for index, line in enumerate(stream):
                        if index > 500000 or len(line) > 8 * 1024 * 1024:
                            warnings.append('session_record_limit: ' + host)
                            break
                        try:
                            event = json.loads(line)
                        except ValueError:
                            warnings.append('malformed_session_record: ' + host)
                            continue
                        if not isinstance(event, dict):
                            continue
                        payload = event.get('payload') or {}
                        if not isinstance(payload, dict):
                            payload = {}
                        if event.get('type') == 'session_meta':
                            sid, cwd = payload.get('id') or sid, payload.get('cwd') or cwd
                        elif event.get('type') == 'turn_context':
                            cwd = payload.get('cwd') or cwd
                        elif host == 'claude':
                            sid, cwd = event.get('sessionId') or sid, event.get('cwd') or cwd
                        stats = counters.setdefault(host + ':' + str(sid), {'messages': {}, 'snapshot': None})
                        if event.get('type') in ('custom-title', 'ai-title'):
                            title = event.get('customTitle') or event.get('aiTitle')
                            if isinstance(title, str) and (event['type'] == 'custom-title' or not stats.get('custom')):
                                stats['title'], stats['custom'] = _safe_text(title, 160), event['type'] == 'custom-title'
                        if host == 'codex' and event.get('type') == 'event_msg' and payload.get('type') == 'token_count':
                            native = (payload.get('info') or {}).get('total_token_usage')
                            if isinstance(native, dict):
                                stats['snapshot'] = native
                        if host == 'codex' and event.get('type') == 'token_usage_record' and payload.get('response_id'):
                            native = payload.get('usage')
                            if isinstance(native, dict):
                                stats['messages'][payload['response_id']] = native
                        message = payload if host == 'codex' and event.get('type') == 'response_item' else event.get('message') or event
                        if not isinstance(message, dict):
                            continue
                        if host == 'claude' and isinstance(message.get('usage'), dict) and message.get('id'):
                            native = message['usage']
                            previous = stats['messages'].get(message['id'], {})
                            stats['messages'][message['id']] = {name: max(previous.get(name, 0), value)
                                for name, value in native.items() if type(value) is int and value >= 0}
                        text = content(message.get('content'))
                        user = message.get('role') == 'user' or event.get('type') == 'user' or event.get('role') == 'user'
                        requested = bool(user and len(text) < 10000 and not text.startswith(('# AGENTS.md', '<environment_context>', '<task-notification>')) and REQUEST.search(text))
                        tools = []
                        if message.get('type') in ('function_call', 'custom_tool_call'):
                            tools = [(message.get('name', ''), message.get('arguments') or message.get('input') or '')]
                        elif isinstance(message.get('content'), list):
                            tools = [(part.get('name', ''), part.get('input') or {}) for part in message['content']
                                     if isinstance(part, dict) and part.get('type') == 'tool_use']
                        observed = any((name == 'Skill' and 'adlc5' in str(args).lower())
                                       or 'adlc5_' in name or KERNEL.search(str(args)) for name, args in tools)
                        if not (requested or observed):
                            continue
                        key = host + ':' + str(sid)
                        when = _safe_text(event.get('timestamp'), 40) or None
                        row = rows.setdefault(key, {'id': _safe_text(sid, 150), 'host': host,
                            'project': _safe_text(Path(str(cwd)).name), 'evidence': 'requested',
                            'workspace_keys': [], 'workspace_labels': {},
                            'first': when, 'last': when, 'tokens': None, 'cost_usd': None,
                            'outcome': 'Not established from transcript', 'sources': 0})
                        if isinstance(cwd, str) and Path(cwd).is_absolute():
                            identity = workspace_key(Path(cwd))
                            if identity not in row['workspace_keys']:
                                row['workspace_keys'].append(identity)
                            row['workspace_labels'][identity] = workspace_label(Path(cwd))
                        row['first'] = min(row['first'] or when or '', when or row['first'] or '') or None
                        row['last'] = max(row['last'] or when or '', when or row['last'] or '') or None
                        if observed:
                            row['evidence'] = 'kernel/skill reference in tool call'
                        actions, features = stats.setdefault('actions', set()), stats.setdefault('features', set())
                        for name, args in tools:
                            text_args = args if isinstance(args, str) else json.dumps(args, default=str)
                            if name == 'Skill' and isinstance(args, dict) and 'adlc5' in str(args.get('skill', '')).lower():
                                actions.add(_safe_text(str(args['skill']), 60))
                            elif 'adlc5_' in name:
                                actions.add(name.rsplit('adlc5_', 1)[1][:40])
                            actions.update(KERNEL_VERB.findall(text_args))
                            if 'adlc5' in name.lower() or 'adlc5' in text_args:
                                features.update(a or b for a, b in FEATURE_ARG.findall(text_args))
                row = rows.get(host + ':' + str(sid))
                if row:
                    row['sources'] += 1
            except OSError:
                warnings.append('session_source_unreadable: ' + host)
    for key, row in rows.items():
        stats = counters.get(key, {})
        values = list(stats.get('messages', {}).values())
        row['token_source'] = 'provider records' if values else 'last cumulative native snapshot' if stats.get('snapshot') else 'Not measured'
        if not values and stats.get('snapshot'):
            values = [stats['snapshot']]
        fields = ('input_tokens', 'output_tokens') if row['host'] == 'codex' else ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens', 'output_tokens')
        row['title'] = stats.get('title')
        row['actions'] = sorted(stats.get('actions', ()))[:12]
        row['features'] = sorted(stats.get('features', ()))[:10]
        if values:
            row['tokens'] = sum(value.get(name, 0) for value in values for name in fields
                                if type(value.get(name)) is int and value[name] >= 0)
    return sorted(rows.values(), key=lambda row: row['last'] or '', reverse=True), files


def collect(roots: list[Path], session_roots: list[tuple[str, Path]], *, active_only=False, observations=()) -> dict:
    warnings = []
    workspaces = discover(roots, warnings)
    features, attempts, runner_hosts = [], {}, {}
    for workspace in workspaces:
        try:
            snapshot = project_workspace(workspace, active_only=active_only)
            key = workspace_key(workspace)
            for item in snapshot['features']:
                item['project'] = workspace.name
                item['workspace_key'] = key
                item['workspace_label'] = workspace_label(workspace)
                item['identity'] = key + '-' + item['identity']
                features.append(item)
            # Native runner results also cover hosts without durable transcript export.
            reader = Reader(workspace)
            attempt_hosts = {}
            for directory in (workspace / '.adlc5', workspace / '.adlc5/_archive'):
                for journal in sorted(directory.glob('*/pilot/attempts.jsonl')):
                    events, _ = _jsonl(reader, journal)
                    for event in events:
                        if event.get('host') in ('claude', 'codex', 'cursor', 'hermes'):
                            attempt_hosts[event.get('attempt_id')] = event['host']
                            runner_hosts.setdefault(key, set()).add(event['host'])
                for path in sorted(directory.glob('*/pilot/results/*.json')):
                    if path.name.endswith(('.schema.json', '.last-message.json', '.session.json', '.usage.json')):
                        continue
                    value = _json(reader, path)
                    if not value or not isinstance(value.get('attempt_id'), str):
                        continue
                    attempt_id = value['attempt_id']
                    row = {'id': _safe_text(attempt_id, 150), 'project': workspace.name,
                           'feature': _safe_text(path.parents[2].name), 'host': _safe_text(value.get('host') or attempt_hosts.get(attempt_id) or 'not recorded'),
                           'status': _safe_text(value.get('status')), 'model': _safe_text(value.get('model_id') or 'unknown'),
                           'session_id': _safe_text(value.get('host_session_id') or value.get('session_id')),
                           'wall_seconds': value.get('wall_seconds') if type(value.get('wall_seconds')) in (int, float) else None}
                    if attempt_id in attempts and attempts[attempt_id] != row:
                        row['status'] = 'conflicting snapshots'
                        warnings.append('conflicting_attempt_snapshot')
                    attempts[attempt_id] = row
            warnings += snapshot['warnings'] + reader.warnings
        except (OSError, ValueError, KeyError, TypeError):
            warnings.append('workspace_capture_unavailable: ' + workspace.name)
    native, files = sessions(session_roots, warnings)
    host_map = {workspace_key(workspace): set(runner_hosts.get(workspace_key(workspace), ())) for workspace in workspaces}
    labels = {workspace_key(workspace): workspace_label(workspace) for workspace in workspaces}
    for session in native:
        for key in session.get('workspace_keys', []):
            host_map.setdefault(key, set()).add(session['host'])
            labels.setdefault(key, session['workspace_labels'][key])
    for observation in observations:
        if isinstance(observation, dict) and re.fullmatch(r'[a-f0-9]{10}', str(observation.get('workspace_key', ''))) and observation.get('host') in ('claude', 'codex', 'cursor', 'hermes'):
            key = observation['workspace_key']
            if key in labels or isinstance(observation.get('workspace_label'), str):
                labels.setdefault(key, _safe_text(observation.get('workspace_label'), 400))
                host_map.setdefault(key, set()).add(observation['host'])
    for feature in features:
        feature['hosts'] = sorted(host_map[feature['workspace_key']])
    inventory, projects = [], {}
    for key, label in sorted(labels.items(), key=lambda item: item[1]):
        path = Path(label).expanduser()
        identity, common = project_identity(path)
        name = common.parent.name if common.name == '.git' else path.name
        inventory.append({'key': key, 'label': label, 'hosts': sorted(host_map[key]), 'project_id': identity})
        project = projects.setdefault(identity, {'id': identity, 'name': _safe_text(name), 'workspace_keys': []})
        project['workspace_keys'].append(key)
    by_tree = {row['key']: row['project_id'] for row in inventory}
    for feature in features:
        feature['project_id'] = by_tree[feature['workspace_key']]
    return {'schema_version': '1.0', 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'status': 'partial' if warnings else 'ok', 'capture': {'scope': 'fleet', 'stable': False},
            'workspace': {'label': 'All projects'}, 'features': features,
            'fleet': {'workspaces': len(labels), 'session_files_scanned': files,
                      'workspace_inventory': inventory, 'projects': list(projects.values()),
                      'sessions': native, 'attempts': list(attempts.values()),
                      'scope': 'Discovered local sources, not a guarantee of complete history. Feature snapshots, host sessions and attempts overlap; do not add them as run counts. Native token subtotals cover whole sessions, may include other work or copied fork prefixes, and must not be added to feature ledgers. Missing cost and independent outcomes stay unmeasured. Regenerate to include new runs.'},
            'warnings': sorted(set(warnings))}
