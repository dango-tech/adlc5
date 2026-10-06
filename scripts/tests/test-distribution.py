#!/usr/bin/env python3
"""Check native archive exclusions and current tracked publication inputs."""
import io
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ('.agents/', '.adlc5/', '.agent-cache/', 'docs/plans/',
             '.cursor/plans/', '.cursor/hooks/state/', '.codex/sessions/',
             '.codex/memories/', '.idea/', '.vscode/', 'marketing/')
PERSONAL_PATH = re.compile(r'/Users/(?!USER\b|username\b|you\b|example\b|test\b)[A-Za-z][A-Za-z0-9_-]+/')
PRIVATE = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|'
                     r'\b(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_\-]{30,}|'
                     r'\bAKIA[A-Z0-9]{16}\b')


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    failures = []
    for name in filter(None, paths):
        path = ROOT / name
        if name.startswith(FORBIDDEN) or Path(name).name.startswith('.env') or name in ('config.yaml', 'PUBLIC-LAUNCH-PLAN.md'):
            failures.append(f'development/private file tracked: {name}')
        if path.is_file():
            content = path.read_text(errors='replace')
            # AWS publishes this exact nonfunctional documentation example.
            if PRIVATE.search(content.replace('AKIAIOSFODNN7EXAMPLE', 'AWS_DOCUMENTATION_EXAMPLE')):
                failures.append(f'possible credential: {name}')
            if PERSONAL_PATH.search(content):
                failures.append(f'personal home path: {name}')
            if name.endswith('.md') and name != 'AGENTS.md' and ('docs/plans/' in content or 'PUBLIC-LAUNCH-PLAN.md' in content or 'claude.ai/code/artifact/' in content):
                failures.append(f'development-plan reference: {name}')
    data = subprocess.check_output(['git', 'archive', '--worktree-attributes', 'HEAD'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        names = set(archive.getnames())
    assert not any(n.startswith(FORBIDDEN + ('.github/',)) or n == 'AGENTS.md' for n in names), 'development files in archive'
    for required in ('scripts/adlc5', '.cursor-plugin/plugin.json', '.cursor/rules/current-information.mdc',
                     '.claude/hooks/claude-usage.sh', '.codex/hooks/codex-usage.sh'):
        assert required in names, f'missing product asset: {required}'
    assert not failures, '\n'.join(failures)  # Paths only; never print potential secrets.
    print('PASS: tracked publication inputs and native archive exclusions')


if __name__ == '__main__':
    main()
