#!/usr/bin/env python3
"""Prepare frozen manual host-agent runs; collect real consumer checks, never fake a run."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def framework_digest(root):
    if (root / '.git').exists():
        names = command(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], root).splitlines()
        paths = [root / name for name in names]
    else:
        paths = [p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    if (root / 'config.yaml').is_file():
        paths.append(root / 'config.yaml')
    value = hashlib.sha256()
    for path in sorted(set(paths)):
        value.update(str(path.relative_to(root)).encode())
        value.update(path.read_bytes() if path.is_file() else b'<deleted>')
    return value.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def command(argv, cwd):
    env = dict(os.environ, GIT_AUTHOR_DATE='2026-10-01T00:00:00Z', GIT_COMMITTER_DATE='2026-10-01T00:00:00Z')
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


def prepare(args):
    bank = json.loads((ROOT / 'templates/evaluation/cases.json').read_text())
    if bank.get('schema_version') != 1:
        raise ValueError('unsupported case bank schema')
    case = next((c for c in bank['cases'] if c['case_id'] == args.case), None)
    if case is None:
        raise ValueError('unknown case')
    if case.get('profile') not in ('tiny', 'standard', 'high_risk') or not isinstance(case.get('task'), str) or not case['task'].strip():
        raise ValueError('case requires canonical profile and nonempty frozen task')
    for field, value in [('observation', case.get('observation_window_hours')), ('wall_clock', (case.get('budget') or {}).get('wall_clock_minutes')), ('cost', (case.get('budget') or {}).get('cost_usd'))]:
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or field != 'cost' and value == 0:
            raise ValueError('case budgets/window must be finite nonnegative numbers; time limits must be positive')
    run = Path(args.directory).resolve()
    run.mkdir(parents=True, exist_ok=False)
    repo = run / 'consumer'
    shutil.copytree(ROOT / 'dogfood/consumer', repo, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy(ROOT / 'scripts/evaluation/acceptance.py', run / 'acceptance.py')
    shutil.copy(repo / 'regression.py', run / 'regression.py')
    command(['git', 'init', '-q', str(repo)], ROOT)
    command(['git', 'add', '.'], repo)
    command(['git', '-c', 'user.name=ADLC5 fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Frozen consumer starting point'], repo)
    revision = command(['git', 'rev-parse', 'HEAD'], repo)
    framework = ROOT
    if args.arm == 'baseline':
        framework = run / 'framework'
        framework.mkdir()
        # tar reads only a trusted repository revision into a new empty directory.
        archive = subprocess.run(['git', 'archive', bank['baseline_framework_revision']], cwd=ROOT, capture_output=True, check=True)
        subprocess.run(['tar', '-x', '-C', str(framework)], input=archive.stdout, check=True)
    manifest = dict(case, arm=args.arm, run_id=run.name, node_id='host-delivery', host=args.host, model=args.model,
                    created_at=datetime.now(timezone.utc).isoformat(), fixture_revision=revision,
                    framework_path=str(framework), framework_sha256=framework_digest(framework), framework_revision=command(['git', 'rev-parse', bank['baseline_framework_revision'] if args.arm == 'baseline' else 'HEAD'], ROOT),
                    fixture_source_sha256={p.name: digest(p) for p in sorted(repo.glob('*.py'))},
                    fixture_case_sha256=hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest(),
                    framework_dirty=bool(command(['git', 'status', '--porcelain'], ROOT)) if args.arm != 'baseline' else False,
                    frozen_files={name: digest(run / name) for name in ('acceptance.py', 'regression.py')},
                    acceptance_command=[sys.executable, str(run / 'acceptance.py'), str(repo), args.case],
                    regression_command=[sys.executable, str(run / 'regression.py')])
    write(run / 'manifest.json', manifest)
    write(run / 'manifest-lock.json', {'sha256': digest(run / 'manifest.json')})
    write(run / 'observations.json', dict(rework=None, human_rejected=None, escaped_defects=None,
        observation_completed_at=None, interventions=None, reviewer_findings=[], quality_gates_passed=None,
        usage=[], telemetry=[]))
    handoff = f'''# Fresh host session handoff\n\nCase: {args.case}; arm: {args.arm}; profile: {case['profile']}\nHost/model: {args.host} / {args.model}\nConsumer: {repo}\nFramework: {framework}\n\n{case['task']}\n\nFrozen acceptance: `{shlex.join(manifest['acceptance_command'])}`\nFrozen regression: `PYTHONPATH={shlex.quote(str(repo))} {shlex.join(manifest['regression_command'])}`. If using a different Python runtime, prepare all arms with that same runtime.\nDo not change the frozen scripts or task. Do not commit consumer implementation.\nFor framework arms invoke @adlc5 for {args.case}, initialize canonical acceptance entries before locking anchors, and use the selected profile. Use this framework path, not your global installation. Follow host-native sessions; record actual calls, interventions and accounting with run_id {run.name} and node_id host-delivery (or matching finer-grained node IDs).\nDirect arm performs the same consumer tests and independent diff review.\nHigh-risk runs require genuine human approval; leave readiness unknown until it occurs.\nResume in a fresh session from manifest.json, feature artifacts/state and kernel pilot/state get output. Never reconstruct progress from chat or assert completion via state set.\nPopulate observations.json from actual telemetry/usage and review; escaped_defects stays null until the {case['observation_window_hours']}-hour observation window finishes. Cost/token source belongs on every usage record. Collection measures elapsed wall time from preparation, including human idle time.\n'''
    (run / 'HANDOFF.md').write_text(handoff)
    print(run / 'HANDOFF.md')


def collect(args):
    run = Path(args.directory).resolve()
    manifest = json.loads((run / 'manifest.json').read_text())
    if digest(run / 'manifest.json') != json.loads((run / 'manifest-lock.json').read_text())['sha256']:
        raise ValueError('frozen manifest changed; prepare a new run')
    observations = json.loads((run / 'observations.json').read_text())
    framework = Path(manifest['framework_path'])
    if framework_digest(framework) != manifest['framework_sha256']:
        raise ValueError('framework changed during run; prepare a new frozen run')
    changed = any(digest(run / name) != sha for name, sha in manifest['frozen_files'].items())
    results = {}
    for kind in ('acceptance', 'regression'):
        started = time.monotonic()
        env = dict(os.environ, PYTHONPATH=str(run / 'consumer'))
        result = subprocess.run(manifest[kind + '_command'], cwd=run / 'consumer', env=env, capture_output=True, text=True, timeout=60)
        (run / (kind + '.log')).write_text(result.stdout + result.stderr)
        results[kind] = dict(exit_code=result.returncode, elapsed_seconds=time.monotonic() - started, output_sha256=digest(run / (kind + '.log')))
    gate_passed = False
    if manifest['arm'] != 'direct':
        policy_query = "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); from lib.policies_load import load_policies, profile_name; print(profile_name(load_policies(Path(sys.argv[2]), sys.argv[3])))"
        actual_profile = subprocess.run([sys.executable, '-c', policy_query, str(framework / 'scripts'), str(run / 'consumer'), manifest['case_id']], capture_output=True, text=True, check=True).stdout.strip()
        gate_passed = actual_profile == manifest['profile']
        results['profile'] = {'selected': actual_profile, 'frozen': manifest['profile'], 'matched': gate_passed}
        for name, argv in [('gate', ['gate', '--gate', 'pr-ready']), ('anchors', ['anchors', 'check'])]:
            result = subprocess.run([sys.executable, str(framework / 'scripts/adlc5'), *argv, '--feature', manifest['case_id'], '--workspace', str(run / 'consumer')], capture_output=True, text=True, timeout=60)
            (run / (name + '.log')).write_text(result.stdout + result.stderr)
            results[name] = dict(exit_code=result.returncode, output_sha256=digest(run / (name + '.log')))
            gate_passed = gate_passed and result.returncode == 0
    else:
        review_path = run / 'independent-review.json'
        if review_path.is_file():
            review = json.loads(review_path.read_text())
            gate_passed = bool(review.get('coder_session_id') and review.get('verifier_session_id') and review['coder_session_id'] != review['verifier_session_id'] and review.get('disposition') == 'pass' and review.get('blocking_findings') == [])
    if framework_digest(framework) != manifest['framework_sha256']:
        raise ValueError('framework changed while collecting checks')
    started = datetime.fromisoformat(manifest['created_at'])
    outcome = dict(run_id=manifest['run_id'], profile=manifest['arm'] + ':' + manifest['profile'], case_id=manifest['case_id'],
        anchors_passed=results['acceptance']['exit_code'] == 0 and not changed, regression_passed=results['regression']['exit_code'] == 0,
        anchor_changed=changed, elapsed_seconds=(datetime.now(timezone.utc) - started).total_seconds(),
        **{k: observations.get(k) for k in ('rework', 'human_rejected', 'escaped_defects', 'interventions', 'reviewer_findings')})
    outcome['quality_gates_passed'] = gate_passed
    completed = observations.get('observation_completed_at')
    if not completed or datetime.fromisoformat(completed) > datetime.now(timezone.utc) or (datetime.fromisoformat(completed) - started).total_seconds() < manifest['observation_window_hours'] * 3600:
        outcome['escaped_defects'] = None
    write(run / 'checks.json', results)
    for name, records in [('outcomes', [outcome]), ('usage', observations['usage']), ('telemetry', observations['telemetry'])]:
        (run / (name + '.jsonl')).write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in records))
    spec = importlib.util.spec_from_file_location('scorer', ROOT / 'scripts/evaluate-runs.py')
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    report = scorer.evaluate(observations['telemetry'], observations['usage'], [outcome])
    report['outcome'] = outcome
    report['consumer_checks'] = results
    report['live_comparison'] = 'manual host execution; collection alone is not a live comparison'
    actual_usage = [entry for entry in observations['usage'] if entry.get('run_id') == manifest['run_id']]
    report['accounting_available'] = bool(actual_usage)
    report['accounting_sources'] = sorted({str(entry.get('source') or 'unknown') for entry in actual_usage})
    report['cost_basis'] = sorted({'reported' if 'cost_usd' in entry else 'estimated' if 'estimated_cost_usd' in (entry.get('extra') or {}) else 'unavailable' for entry in actual_usage})
    for bucket in report['by_profile'].values():
        if any('cost_usd' not in entry and 'estimated_cost_usd' not in (entry.get('extra') or {}) for entry in actual_usage):
            bucket['cost_usd'] = bucket['failed_cost_usd'] = None
        if any('total' not in (entry.get('tokens') or {}) for entry in actual_usage):
            bucket['tokens'] = bucket['failed_tokens'] = None
    if not actual_usage:
        for bucket in report['by_profile'].values():
            for field in ('tokens', 'cost_usd', 'failed_tokens', 'failed_cost_usd'):
                bucket[field] = None
    write(run / 'report.json', report)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='operation', required=True)
    p = subs.add_parser('prepare')
    p.add_argument('--case', required=True)
    p.add_argument('--arm', choices=['direct', 'baseline', 'candidate'], required=True)
    p.add_argument('--host', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--directory', required=True)
    p = subs.add_parser('collect')
    p.add_argument('--directory', required=True)
    args = parser.parse_args()
    try:
        (prepare if args.operation == 'prepare' else collect)(args)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
