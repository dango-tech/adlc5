#!/usr/bin/env python3
"""Conservative PR-wide test selection; unknown/shared changes require full CI."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def plan(paths):
    selected = set()
    reasons = []
    for path in paths:
        if path.startswith('assets/brand/'):
            suites = {'docs', 'pulse', 'packages'}
        elif path.startswith(('docs/', 'website/')) or path in ('README.md', 'mkdocs.yml', 'requirements-docs.txt'):
            suites = {'docs'}
        elif path.startswith('shared/pulse/'):
            suites = {'pulse', 'packages'}
        elif path in ('scripts/pulse.py', 'scripts/pulse-statusline.py', 'scripts/lib/pulse.py', 'scripts/lib/pulse_fleet.py', 'scripts/lib/pulse_settings.py'):
            suites = {'pulse', 'platforms', 'packages', 'install'}
        elif path in ('scripts/tests/test-pulse.py', 'scripts/tests/test-pulse-fleet.py'):
            suites = {'pulse'}
        elif path.startswith('telemetry-intake/'):
            suites = {'telemetry'}
        elif path in ('scripts/runner/questions.py', 'scripts/runner/answer.py', 'scripts/lib/requirements_readiness.py'):
            suites = {'runner', 'packages'}
        else:
            suites = {'full', 'platforms', 'packages', 'install', 'docs', 'telemetry'}
        selected.update(suites)
        reasons.append({'path': path, 'suites': sorted(suites)})
    if not paths:
        selected.update(('full', 'platforms', 'packages', 'install', 'docs', 'telemetry'))
    return {**{name: name in selected for name in ('full', 'pulse', 'runner', 'platforms', 'packages', 'install', 'docs', 'telemetry')}, 'reasons': reasons}


def check_results(jobs):
    flags = jobs['changes'].get('outputs', {})
    names = ('full', 'pulse', 'runner', 'platforms', 'packages', 'install', 'docs', 'telemetry')
    if any(flags.get(name) not in ('true', 'false') for name in names):
        raise ValueError('Missing or invalid test-selection outputs')
    required = {'changes', 'privacy', 'windows'}
    if any(flags[name] == 'true' for name in ('full', 'platforms', 'install')):
        required.add('test')
    if flags['pulse'] == 'true' and 'test' not in required:
        required.add('pulse')
    if flags['full'] != 'true':
        for name in ('packages', 'runner'):
            if flags[name] == 'true': required.add(name)
    for name in ('telemetry', 'docs'):
        if flags[name] == 'true': required.add(name)
    failed = [name for name in required if jobs.get(name, {}).get('result') != 'success']
    failed += [name for name, job in jobs.items() if job['result'] in ('failure', 'cancelled')]
    if failed:
        raise ValueError('Required validation incomplete: ' + ', '.join(sorted(set(failed))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--output')
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        check_results(json.loads(os.environ['RESULTS']))
        print('All selected validation completed successfully.')
        return
    if not args.base:
        parser.error('--base is required when computing a plan')
    # Merge-base comparison includes the entire PR; NUL paths preserve whitespace.
    result = subprocess.run(['git', 'diff', '--name-only', '-z', '--no-renames', args.base + '...' + args.head], capture_output=True, check=True)
    paths = [p for p in result.stdout.decode().split('\0') if p]
    data = plan(['full validation requested'] if args.full else paths)
    if args.output:
        with Path(args.output).open('a') as stream:
            for key, value in data.items():
                if key != 'reasons':
                    stream.write(f'{key}={str(value).lower()}\n')
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
