"""Safe, read-only Settings projection using the execution configuration resolver."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import shutil

from lib.config_layers import effective_config, config_paths, project_identity, read_layer

VISIBLE = ('default_host', 'model_routing', 'platform_profiles', 'platform_modes', 'persona_mode', 'defaults', 'git_branch_prefix')
SENSITIVE = re.compile(r'secret|password|token|credential|api.?key|authorization', re.I)
TOKEN = re.compile(r'(?:sk-|ghp_|github_pat_|Bearer\s)', re.I)


def safe(value):
    if isinstance(value, str):
        return 'Configured (redacted)' if TOKEN.search(value) else value[:400].replace(str(Path.home()), '~')
    if isinstance(value, dict):
        return {key: 'Configured (redacted)' if SENSITIVE.search(key) else safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [safe(item) for item in value[:100]]
    return value


def snapshot(workspace: Path | None, *, scope='worktree'):
    layers = [{'layer': layer, 'path': safe(str(path)), 'present': path.is_file()} for layer, path in config_paths(workspace) if scope != 'project' or layer != 'worktree']
    try:
        _values, rows = effective_config(workspace, scope=scope)
        rows = [safe(row) for row in rows if row['key'].split('.')[0] in VISIBLE and not SENSITIVE.search(row['key'])]
        error = None
    except (ValueError, OSError):
        rows, error = [], 'Invalid or unreadable configuration; effective settings unavailable.'
    present = {row['key'] for row in rows}
    for key, value in ({} if error else {'default_host': 'Not configured', 'defaults.summary': 'brief', 'model_routing.strategy': 'balanced'}).items():
        if key not in present:
            rows.append({'key': key, 'value': value, 'source': 'built-in', 'layer': 'built-in', 'status': 'inherited', 'history': []})
    try:
        for key, value in read_layer(Path.home() / '.adlc5/install.yaml').items():
            if key.endswith('_target') or key == 'install_backup_root':
                rows.append({'key': 'installation.' + key, 'value': safe(value), 'source': '~/.adlc5/install.yaml',
                             'layer': 'machine installation', 'status': 'inherited', 'history': []})
    except (ValueError, OSError):
        error = error or 'Invalid or unreadable machine installation settings.'
    consent = False
    if workspace:
        try:
            path = workspace / '.adlc5/telemetry/sharing-consent.json'
            if not path.is_symlink() and path.stat().st_size < 4096:
                consent = json.loads(path.read_text()) == {'schema_version': 1, 'enabled': True}
        except (ValueError, OSError):
            pass
    return {'layers': layers, 'rows': sorted(rows, key=lambda row: row['key']), 'error': error,
            'telemetry': 'Explicitly enabled for this workspace' if consent else 'Not enabled for this scope',
            'storage': {'shared_home': '~/.adlc5', 'report': '~/.adlc5/pulse/board.html',
                        'installation_config': '~/.adlc5/install.yaml',
                        'feature_state': safe(str(workspace / '.adlc5')) if workspace else 'Owned by each consumer workspace',
                        'project_config': '~/.adlc5/projects/' + project_identity(workspace)[0] + '/config.yaml' if workspace else 'Select a project',
                        'worktree_override': safe(str(workspace / '.adlc5/overrides.yaml')) if workspace else 'Select a worktree'},
            'credentials': {name: 'Configured' if os.environ.get(name) else 'Not present in board process environment'
                            for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENROUTER_API_KEY')}}


def integrations(root: Path):
    version = (root / 'core/VERSION').read_text().strip()
    patterns = {'codex': '.codex/plugins/cache/*/adlc5/*/.codex-plugin/plugin.json',
                'claude': '.claude/plugins/cache/*/adlc5/*/.claude-plugin/plugin.json',
                'cursor': '.cursor/plugins/cache/*/adlc5/*/.cursor-plugin/plugin.json'}
    result = []
    for host, binary in (('codex', 'codex'), ('claude', 'claude'), ('cursor', 'cursor-agent'), ('hermes', 'hermes')):
        versions = set()
        for path in list(Path.home().glob(patterns[host]))[:200] if host in patterns else []:
            try:
                if not path.is_symlink() and path.stat().st_size < 65536:
                    value = json.loads(path.read_text()).get('version')
                    if isinstance(value, str):
                        versions.add(safe(value))
            except (OSError, ValueError):
                pass
        result.append({'host': host, 'cli_available': bool(shutil.which(binary)), 'cached_versions': sorted(versions),
                       'runtime_version': version, 'status': 'Different cached versions found' if versions - {version} else 'No mismatch observed' if versions else 'Installed plugin version not established'})
    return result


def shared_runtime():
    try:
        path = Path.home() / '.adlc5/runtime.json'
        if path.is_symlink() or path.stat().st_size > 8192:
            raise ValueError('invalid runtime registry')
        value = json.loads(path.read_text())
        return {key: safe(value.get(key)) for key in ('version', 'digest', 'path')}
    except (OSError, ValueError, AttributeError):
        return {'path': 'No shared runtime staged; use adlc5 setup storage'}
