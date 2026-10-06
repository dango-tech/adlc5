#!/usr/bin/env python3
"""Fail closed on private data in the index and reachable history; print paths only."""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ('.agents/', '.adlc5/', '.agent-cache/', 'docs/plans/', 'marketing/',
             '.cursor/plans/', '.cursor/hooks/state/', '.codex/sessions/', '.codex/memories/')
SECRET = re.compile(rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_\-]{30,}|\bAKIA[A-Z0-9]{16}\b')
HOME = re.compile(rb'/(?:Users|home)/(?!USER\b|username\b|user\b|you\b|example\b|test\b)[A-Za-z][A-Za-z0-9_-]+/|[A-Za-z]:\\Users\\(?!username\\|user\\)[^\\\s]+\\')
EMAIL = re.compile(rb'\b[A-Za-z0-9_.+\-]+@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b')
ALLOWED_EMAIL_DOMAINS = {b'example.com', b'example.org', b'example.invalid', b'example.test', b'users.noreply.github.com'}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def problems(name, data):
    out = []
    if name.startswith(FORBIDDEN) or name in ('config.yaml', 'PUBLIC-LAUNCH-PLAN.md') or Path(name).name.startswith('.env'):
        out.append('private/development artifact')
    if SECRET.search(data.replace(b'AKIAIOSFODNN7EXAMPLE', b'AWS_DOCUMENTATION_EXAMPLE')):
        out.append('possible credential')
    if HOME.search(data):
        out.append('personal filesystem path')
    if re.search(rb'https://claude[.]ai/code/artifact/[a-f0-9-]{36}', data):
        out.append('private artifact link')
    if name.endswith('.md') and (b'PUBLIC-LAUNCH-PLAN.md' in data or b'docs/plans/' in data or b'## Learned User Preferences' in data):
        out.append('private development context')
    emails = data.replace(b'noreply@github.com', b'noreply@example.invalid').replace(b'noreply@anthropic.com', b'noreply@example.invalid')
    if any(m.group(1).lower() not in ALLOWED_EMAIL_DOMAINS for m in EMAIL.finditer(emails)):
        out.append('non-public email')
    return out


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--self-test', action='store_true'); parser.add_argument('--pre-commit', action='store_true'); args = parser.parse_args()
    if args.self_test:
        assert problems('x.txt', b'person' + b'@' + b'company.invalid') == ['non-public email']
        assert problems('x.txt', b'/Users/' + b'person/project/') == ['personal filesystem path']
        assert problems('.cursor/hooks/state/local.json', b'{}')
        assert not problems('x.txt', b'test@example.invalid contributors@users.noreply.github.com')
        print('PASS: privacy rule regressions'); return
    if args.pre_commit:
        for identity in ('GIT_AUTHOR_IDENT', 'GIT_COMMITTER_IDENT'):
            email = re.search(rb'<([^>]+)>', git('var', identity))
            if email is None or not email.group(1).endswith(b'@users.noreply.github.com'):
                raise SystemExit('Commit requires a GitHub noreply identity; no private email was printed')
    objects = {}
    for entry in git('ls-files', '-s', '-z').split(b'\0'):
        if entry:
            meta, name = entry.split(b'\t', 1); objects.setdefault(meta.split()[1].decode(), set()).add(name.decode())
    for entry in git('rev-list', '--objects', '--all').decode().splitlines():
        oid, _, name = entry.partition(' ')
        if name: objects.setdefault(oid, set()).add(name)
    failures = []
    proc = subprocess.Popen(['git', '-C', str(ROOT), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for oid, names in objects.items():
        proc.stdin.write((oid+'\n').encode()); proc.stdin.flush(); header = proc.stdout.readline().split()
        if len(header) != 3: raise RuntimeError('missing publication object')
        data = proc.stdout.read(int(header[2])); proc.stdout.read(1)
        if header[1] == b'blob':
            for name in names:
                for reason in problems(name, data): failures.append(f'{reason}: {name} ({oid[:12]})')
    proc.stdin.close(); proc.wait()
    for line in git('log', '--all', '--format=%H%x09%ae%x09%ce').decode().splitlines():
        oid, author, committer = line.split('\t')
        if any(not e.endswith('@users.noreply.github.com') and e != 'noreply@github.com' for e in (author, committer)):
            failures.append(f'non-public commit email: {oid[:12]}')
    failures.extend('commit-message '+r for r in problems('commit-message', git('log', '--all', '--format=%B')))
    if failures: raise SystemExit('\n'.join(sorted(set(failures))))
    print('PASS: publication index, reachable history and commit metadata')


if __name__ == '__main__':
    main()
