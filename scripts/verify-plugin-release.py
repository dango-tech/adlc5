#!/usr/bin/env python3
"""Validate the complete four-host release before publishing its existing bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


def verify(directory, version):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Expected a semantic release version')
    expected = {f'adlc5-{host}-plugin-{version}.{suffix}'
                for host in ('codex', 'claude-code', 'cursor', 'hermes')
                for suffix in ('zip', 'tar.gz')}
    lines = (directory / 'SHA256SUMS').read_text().splitlines()
    checksums = {}
    for line in lines:
        checksum, name = line.split('  ')
        if name not in expected or name in checksums or not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise ValueError('Unexpected or duplicate release checksum entry')
        checksums[name] = checksum
    if set(checksums) != expected:
        raise ValueError('Release must include exactly eight host archives')
    revisions = set()
    for name, checksum in checksums.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != checksum:
            raise ValueError('Archive checksum mismatch: ' + name)
        if name.endswith('.zip'):
            with zipfile.ZipFile(directory / name) as archive:
                metadata = json.loads(archive.read('INSTALL.json'))
            host = 'claude-code' if metadata['host'] == 'claude' else metadata['host']
            if name != f'adlc5-{host}-plugin-{version}.zip' or metadata['version'] != version:
                raise ValueError('Archive host/version does not match release')
            if metadata.get('source_dirty') is not False or not re.fullmatch(r'[0-9a-f]{40}', metadata['source_revision']):
                raise ValueError('Release requires clean source provenance')
            revisions.add(metadata['source_revision'])
    if len(revisions) != 1:
        raise ValueError('Host packages must share one source revision')
    return revisions.pop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    print('Verified release source: ' + verify(args.directory, args.version))
