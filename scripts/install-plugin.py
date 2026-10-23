#!/usr/bin/env python3
"""Install an extracted host package through the host's supported local flow."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from pulse import _cache_dir


def inventory(package):
    files = []
    total = 0
    digest = hashlib.sha256()
    for path in sorted(package.rglob('*')):
        if '.git' in path.relative_to(package).parts:
            continue
        if path.is_symlink():
            raise ValueError('Package symlinks are not accepted')
        if path.is_dir():
            continue
        if not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError('Invalid package file')
        total += path.stat().st_size
        if len(files) >= 10000 or total > 128 * 1024 * 1024:
            raise ValueError('Package input limit exceeded')
        relative = path.relative_to(package).as_posix()
        if '__pycache__' in path.parts or relative.endswith('.pyc'):
            continue
        digest.update(relative.encode() + b'\0' + path.read_bytes())
        files.append(relative)
    return digest.hexdigest()[:20]


def commands(host, source, marketplace):
    if host == 'codex':
        return [['codex', 'plugin', 'marketplace', 'add', str(marketplace)]]
    if host == 'claude':
        return [['claude', 'plugin', 'marketplace', 'add', str(marketplace)], ['claude', 'plugin', 'install', 'adlc5@adlc5-local']]
    if host == 'hermes':
        return [['git', '-C', str(source), 'init', '-q'], ['git', '-C', str(source), 'add', '-A'],
                ['git', '-C', str(source), '-c', 'user.name=ADLC5 package installer', '-c', 'user.email=installer@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-qm', 'Local ADLC5 package'],
                ['hermes', 'plugins', 'install', source.as_uri(), '--no-enable']]
    return []


def install(package, dry_run=False):
    metadata = json.loads((package / 'INSTALL.json').read_text())
    host, version = metadata['host'], metadata['version']
    if host not in ('codex', 'claude', 'cursor', 'hermes') or not isinstance(version, str) or any(c not in '0123456789abcdefghijklmnopqrstuvwxyz.-' for c in version) or not version:
        raise ValueError('Invalid host package metadata')
    identity = inventory(package)
    base = Path.home() / '.adlc5/packages' / host / version / identity
    source = base / 'plugin'
    marketplace = base / 'marketplace'
    actions = commands(host, source, marketplace)
    if dry_run:
        return {'status': 'dry-run', **metadata, 'source': str(source), 'commands': actions,
                'cursor_destination': str(Path.home() / '.cursor/plugins/local/adlc5') if host == 'cursor' else None}
    for action in actions:
        if not shutil.which(action[0]):
            raise ValueError(action[0] + ' CLI is not available on PATH')
    base = _cache_dir(Path.home(), ('.adlc5', 'packages', host, version, identity))
    if source.exists():
        if source.is_symlink() or inventory(source) != identity:
            raise ValueError('Staged package was modified; refusing to overwrite it')
    else:
        temp = Path(tempfile.mkdtemp(prefix='.install-', dir=base))
        try:
            shutil.copytree(package, temp / 'plugin', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            os.replace(temp / 'plugin', source)
        finally:
            shutil.rmtree(temp)
    if host in ('codex', 'claude'):
        # Reuse the builder's host-specific marketplace contract.
        import importlib.util
        spec = importlib.util.spec_from_file_location('packager_install', ROOT / 'scripts/package-plugin.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        if not marketplace.exists():
            module.write_marketplace(marketplace, host, source)
    backup = None
    if host == 'cursor':
        parent = _cache_dir(Path.home(), ('.cursor', 'plugins', 'local'))
        target = parent / 'adlc5'
        if target.exists() or target.is_symlink():
            if target.is_symlink() or not (target / '.adlc5-package.json').is_file():
                raise ValueError('Existing Cursor destination is not a managed ADLC5 package; move it manually')
            backup = parent / ('adlc5.backup-' + str(time.time_ns()))
            target.rename(backup)
        try:
            shutil.copytree(source, target)
        except Exception:
            if target.exists(): shutil.rmtree(target)
            if backup: backup.rename(target)
            raise
    else:
        for action in actions:
            subprocess.run(action, check=True)
    next_steps = {'codex': 'Open Codex Plugins, select ADLC5 local build, and install/reinstall adlc5.',
                  'claude': 'Restart Claude Code. For an existing installation, refresh the marketplace and update adlc5@adlc5-local.',
                  'cursor': 'Reload Cursor, review and enable the ADLC5 local plugin.',
                  'hermes': 'Review the package, then run hermes plugins enable adlc5 and start a new session.'}
    return {'status': 'prepared' if host == 'codex' else 'installed', **metadata, 'source': str(source),
            'backup': str(backup) if backup else None, 'next': next_steps[host]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', default=str(ROOT))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(install(Path(args.package).resolve(), args.dry_run), indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print('Plugin installation failed: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
