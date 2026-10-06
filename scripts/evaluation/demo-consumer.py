#!/usr/bin/env python3
"""Scripted kernel contract demo; not live host delivery or independent review."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, help='new disposable directory')
    args = parser.parse_args()
    run = Path(args.directory).resolve()
    subprocess.run([sys.executable, str(ROOT / 'scripts/evaluation/run-case.py'), 'prepare', '--case', 'tiny-label', '--arm', 'candidate', '--host', 'scripted-contract-demo', '--model', 'none', '--directory', str(run)], check=True, capture_output=True)
    repo = run / 'consumer'
    subprocess.run(['bash', str(ROOT / 'scripts/init-feature.sh'), '--workspace', str(repo), '--feature', 'tiny-label', '--mode', 'brownfield', '--scope', 'increment'], check=True, capture_output=True)
    feature = repo / '.adlc5/tiny-label'
    (feature / 'policies.yaml').write_text((ROOT / 'templates/policies-tiny.yaml.example').read_text())
    (feature / 'risk.json').write_text(json.dumps({'categories': [], 'uncertain': False, 'rationale': 'Scripted whitespace-only internal label behavior; no public API promise.'}))
    manifest = json.loads((run / 'manifest.json').read_text())
    commands = [{'id': name, 'command': shlex.join(manifest[name + '_command']), 'required': True} for name in ('acceptance', 'regression')]
    # Frozen regression lives outside the app and imports app via PYTHONPATH.
    commands[1]['command'] = 'PYTHONPATH=' + shlex.quote(str(repo)) + ' ' + commands[1]['command']
    (feature / 'evidence/checks.json').write_text(json.dumps(commands))
    kernel = [sys.executable, str(ROOT / 'scripts/adlc5')]
    flags = ['--feature', 'tiny-label', '--workspace', str(repo)]

    def invoke(argv):
        result = subprocess.run(kernel + argv + flags, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    before = (feature / 'state.json').read_bytes()
    status, rejected = invoke(['transition', 'completed'])
    assert status != 0 and (feature / 'state.json').read_bytes() == before
    status, failed = invoke(['evidence', 'check'])
    assert status != 0 and any(r['status'] == 'fail' for r in failed['results'])
    app = repo / 'app.py'
    app.write_text(app.read_text().replace('return name.strip().title()', 'return name.strip()'))
    status, checked = invoke(['evidence', 'check'])
    assert status == 0, checked
    # Each invocation is a new process. State restoration uses files, never chat.
    status, advanced = invoke(['transition', 'specify-4-handoff'])
    assert status == 0, advanced
    restored = subprocess.run(kernel + ['state', 'get'] + flags, check=True, capture_output=True, text=True)
    assert 'specify-4-handoff' in restored.stdout
    status, blocked = invoke(['gate', '--gate', 'pr-ready'])
    assert status != 0, 'checks alone must not authorize completion without review/lifecycle artifacts'
    summary = {'kind': 'scripted-contract-demo', 'live_agent_delivery': False, 'checks_passed': True,
               'invalid_completion_rejected': True, 'resumed_step': 'specify-4-handoff',
               'completion_without_review_blocked': True, 'human_approval_recorded': False}
    (run / 'demo-result.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
