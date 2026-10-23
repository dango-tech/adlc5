#!/usr/bin/env python3
"""Stage one content-addressed shared runtime without moving user configuration."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from pulse import _atomic_write, _cache_dir


def stage(source: Path):
    spec = importlib.util.spec_from_file_location('adlc5_packager', source / 'scripts/package-plugin.py')
    packager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packager)
    if (source / '.adlc5-package.json').is_file() or (source / '.adlc5-runtime.json').is_file():
        names = packager.selected([p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()], source)
    else:
        names = packager.selected(packager.candidates(source), source)
    digest = hashlib.sha256()
    entries = []
    for name in names:
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('runtime source must contain regular files: ' + name)
        raw = path.read_bytes()
        if packager.SECRET.search(raw.replace(b'AKIAIOSFODNN7EXAMPLE', b'AWS_DOCUMENTATION_EXAMPLE')) or packager.HOME.search(raw):
            raise ValueError('runtime publication scan failed: ' + name)
        mode = 0o755 if os.access(path, os.X_OK) else 0o644
        digest.update(name.encode() + b'\0' + str(mode).encode() + b'\0' + raw)
        entries.append((name, raw, mode))
    version = (source / 'core/VERSION').read_text().strip()
    if not version or any(c not in '0123456789abcdefghijklmnopqrstuvwxyz.-' for c in version):
        raise ValueError('invalid runtime version')
    identity = digest.hexdigest()[:20]
    home = Path.home()
    parent = _cache_dir(home, ('.adlc5', 'runtimes', version))
    target = parent / identity
    if target.is_symlink():
        raise ValueError('runtime target is unsafe')
    if not target.exists():
        temp = Path(tempfile.mkdtemp(prefix='.stage-', dir=parent))
        try:
            for name, raw, mode in entries:
                path = temp / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                path.chmod(mode)
            _atomic_write(temp / '.adlc5-runtime.json', json.dumps({'version': version, 'digest': identity}).encode())
            _atomic_write(temp / '.adlc5-package.json', packager.build_manifest(version))
            try:
                temp.rename(target)
            except OSError:
                if not target.is_dir():
                    raise
        finally:
            if temp.exists():
                shutil.rmtree(temp)
    # Never overwrite or silently reuse a modified supposedly immutable runtime.
    for name, raw, mode in entries:
        path = target / name
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError('shared runtime was modified: ' + name)
    _atomic_write(home / '.adlc5/runtime.json', json.dumps({'version': version, 'digest': identity, 'path': str(target)}).encode())
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=str(ROOT))
    args = parser.parse_args()
    try:
        print(stage(Path(args.source).resolve()).as_posix())
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
