"""Paths and small helpers for ADLC5's machine and repository config layers."""
from __future__ import annotations

import subprocess
import hashlib
import json
from pathlib import Path


def project_identity(workspace: Path) -> tuple[str, Path]:
    workspace = workspace.resolve()
    proc = subprocess.run(['git', '-C', str(workspace), 'rev-parse', '--git-common-dir'], capture_output=True, text=True, check=False)
    common = Path(proc.stdout.strip()) if proc.returncode == 0 else workspace
    if not common.is_absolute():
        common = (workspace / common).resolve()
    common = common.resolve()
    return hashlib.sha256(str(common).encode()).hexdigest()[:16], common


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
        elif legacy.exists() and not any(path == legacy for _, path in paths):
            paths.append(("legacy_repo", legacy))
    else:
        paths.append(("repo", workspace / ".adlc5" / "config.yaml"))
    identity, _ = project_identity(workspace)
    paths.append(('project', Path.home() / '.adlc5/projects' / identity / 'config.yaml'))
    paths.append(('worktree', workspace / '.adlc5/overrides.yaml'))
    return paths


def merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def read_layer(path: Path) -> dict:
    if not path.exists():
        return {}
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('invalid or oversized configuration: ' + path.name)
    text = path.read_text(encoding='utf-8')
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError:
            from lib.simple_yaml import parse
            value = parse(text)
        else:
            try:
                value = yaml.safe_load(text)
            except yaml.YAMLError:
                raise ValueError('malformed configuration: ' + path.name) from None
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('configuration must be a mapping: ' + path.name)
    try:
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError):
        raise ValueError('configuration contains unsupported values: ' + path.name) from None
    return value


def leaves(value, prefix=''):
    for key, item in value.items():
        name = prefix + str(key)
        if isinstance(item, dict):
            yield from leaves(item, name + '.')
        else:
            yield name, item


def effective_config(workspace: Path | None, explicit: dict | None = None, *, scope='worktree'):
    """One resolver for execution and display; derived caches are never layers."""
    values, rows, sources, history = {}, {}, {}, {}
    enforced = {}
    for layer, path in config_paths(workspace):
        if scope == 'project' and layer == 'worktree':
            continue
        overlay = read_layer(path)
        if layer == 'master':
            enforced = overlay.pop('enforced', {})
            if not isinstance(enforced, dict):
                raise ValueError('enforced configuration must be a mapping')
        elif 'enforced' in overlay:
            raise ValueError('only machine configuration may declare enforced settings')
        values = merge(values, overlay)
        for key, value in leaves(overlay):
            history.setdefault(key, []).append({'layer': layer, 'value': value, 'source': str(path)})
            sources[key] = str(path)
            rows[key] = {'key': key, 'value': value, 'layer': layer, 'source': str(path),
                         'status': 'overridden' if len(history[key]) > 1 else 'inherited'}
    if explicit:
        locked = dict(leaves(enforced))
        if any(key in locked and locked[key] != value for key, value in leaves(explicit)):
            raise ValueError('explicit option conflicts with enforced machine configuration')
        values = merge(values, explicit)
        for key, value in leaves(explicit):
            rows[key] = {'key': key, 'value': value, 'layer': 'session', 'source': 'explicit options', 'status': 'overridden'}
    values = merge(values, enforced)
    for key, value in leaves(enforced):
        rows[key] = {'key': key, 'value': value, 'layer': 'master', 'source': str(Path.home() / '.adlc5/config.yaml'), 'status': 'enforced'}
    for key in rows:
        rows[key]['history'] = history.get(key, [])
    return values, list(rows.values())
