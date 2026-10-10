"""Supported-operation evidence, not authentication against writable local files."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
from lib.state_v2 import load_feature_state, set_feature_state, is_human_approver
from lib.policies_load import load_policies, find_policies_path, profile_name, next_step_for_profile, profile_risk_errors, step_enabled

ROOT = Path(__file__).resolve().parents[2]


def folder(workspace, feature):
    if not feature or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in feature):
        raise ValueError('invalid feature name')
    return workspace / '.adlc5' / feature / 'evidence'


def fingerprint(workspace: Path, feature: str) -> str:
    """Hash HEAD/index/working inputs; exclude generated state/logs."""
    # ponytail: full repository scan; scope fingerprints only if measured latency matters.
    h = hashlib.sha256()
    head = subprocess.run(['git', '-C', str(workspace), 'rev-parse', 'HEAD'], capture_output=True, check=True).stdout
    h.update(head)
    h.update(subprocess.run(['git', '-C', str(workspace), 'ls-files', '-s', '-z'], capture_output=True, check=True).stdout)
    state = load_feature_state(workspace, feature) or {}
    contract = {"tasks": [{k: v for k, v in story.items() if k != "status"} for story in (state.get("tasks") or {}).get("stories", [])], "scope": state.get("scope"), "git": state.get("git"), "acceptance_anchor": state.get("acceptance_anchor")}
    h.update(json.dumps(contract, sort_keys=True).encode())
    proc = subprocess.run(['git', '-C', str(workspace), 'ls-files', '-co', '--exclude-standard', '-z'], capture_output=True, check=True)
    names = set(proc.stdout.decode().split('\0')) - {''}
    for story in (state.get('tasks') or {}).get('stories', []):
        names.update(story.get('files') or [])
    names.add('config.yaml')
    policy_path = find_policies_path(workspace, feature)
    if policy_path is not None:
        names.add(str(policy_path.relative_to(workspace)))
    qa = workspace / '.qa' / feature
    if qa.exists():
        names.update(str(p.relative_to(workspace)) for p in qa.rglob('*') if p.is_file())
    base = workspace / '.adlc5' / feature
    if base.exists():
        names.update(str(p.relative_to(workspace)) for p in base.rglob('*') if p.is_file())
    from lib.simple_yaml import load_frontmatter
    for spec in (base / 'tasks/code-spec').glob('*.md'):
        fm, _ = load_frontmatter(spec.read_text())
        if fm:
            names.update(fm.get('files_to_create') or [])
            names.update(fm.get('files_to_modify') or [])
            names.update(t.get('file') for t in fm.get('tests', []) if isinstance(t, dict) and t.get('file'))
    for name in sorted(names):
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('declared fingerprint path escapes workspace')
        parts = Path(name).parts
        if '/verify/deterministic-report-' in name and name.endswith('.json'):
            continue
        if '.git' in parts or '__pycache__' in parts or name.endswith('.pyc'):
            continue
        if name.startswith('.agent-cache/') or name.startswith(f'.adlc5/{feature}/pilot/') or name.startswith('.adlc5/') and (name.endswith('/state.json') or '/memory/' in name or '/telemetry/' in name or '/evidence/' in name and not name.endswith('/evidence/checks.json')):
            continue
        path = workspace / name
        h.update(name.encode())
        if path.is_symlink():
            h.update(str(path.readlink()).encode())
            if path.is_file():
                h.update(path.read_bytes())
        elif path.is_file():
            h.update(path.read_bytes())
            h.update(str(path.stat().st_mode & 0o777).encode())
        else:
            h.update(b'<deleted>')
    return h.hexdigest()


def append(workspace, feature, event):
    dest = folder(workspace, feature)
    dest.mkdir(parents=True, exist_ok=True)
    event['time'] = datetime.now(timezone.utc).isoformat()
    with (dest / 'completion.jsonl').open('a') as stream:
        stream.write(json.dumps(event) + '\n')


def records(workspace, feature):
    path = folder(workspace, feature) / 'completion.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def config(workspace, feature):
    path = folder(workspace, feature) / 'checks.json'
    if not path.is_file():
        raise ValueError('missing evidence/checks.json: declare required named commands')
    checks = json.loads(path.read_text())
    if not isinstance(checks, list) or not checks:
        raise ValueError('checks.json must be a nonempty array')
    if any(not isinstance(c, dict) or not isinstance(c.get('required', True), bool) or not isinstance(c.get('cwd', '.'), str) for c in checks):
        raise ValueError('each check requires object, boolean required, string cwd')
    if not any(c.get('required', True) and c.get('id') in ('acceptance', 'regression', 'tests') for c in checks):
        raise ValueError('declare a required acceptance, regression, or tests command')
    ids = [c.get('id') for c in checks]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('check IDs must be unique nonempty strings')
    if any(type(c.get('timeout_seconds', 300)) is not int or c.get('timeout_seconds', 300) <= 0 for c in checks):
        raise ValueError('timeout_seconds must be a positive integer')
    return checks


def run_checks(workspace, feature):
    checks = config(workspace, feature)
    before = fingerprint(workspace, feature)
    results = []
    dest = folder(workspace, feature)
    for index, item in enumerate(checks):
        command = item.get('command')
        if not isinstance(command, str) or not command.strip():
            results.append({'id': item['id'], 'required': item.get('required', True), 'status': 'unsupported'})
            continue
        cwd = (workspace / item.get('cwd', '.')).resolve()
        if not cwd.is_relative_to(workspace.resolve()):
            raise ValueError('check cwd must be inside workspace')
        output = dest / f'check-{index}-{before[:16]}-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")}.log'
        timeout = item.get('timeout_seconds', 300)
        with output.open('w') as stream:
            try:
                proc = subprocess.run(command, shell=True, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                results.append({'id': item['id'], 'required': item.get('required', True), 'command': command, 'cwd': str(cwd), 'status': 'fail', 'reason': f'timeout after {timeout} seconds', 'output': str(output.relative_to(workspace))})
                continue
        results.append({'id': item['id'], 'required': item.get('required', True), 'command': command, 'cwd': str(cwd), 'exit_code': proc.returncode, 'status': 'pass' if proc.returncode == 0 else 'fail', 'output': str(output.relative_to(workspace))})
    event = {'kind': 'checks', 'fingerprint': before, 'stable': before == fingerprint(workspace, feature), 'results': results}
    append(workspace, feature, event)
    return event


def completion_checks(workspace, feature, policies=None, *, approval=True, review=True):
    try:
        required = config(workspace, feature)
        current = fingerprint(workspace, feature)
        fresh = [r for r in records(workspace, feature) if r.get('fingerprint') == current]
        latest = next((r for r in reversed(fresh) if r.get('kind') == 'checks'), {})
        results = {r['id']: r for r in latest.get('results', [])}
        failures = [c['id'] for c in required if c.get('required', True) and (results.get(c['id'], {}).get('status') != 'pass' or not latest.get('stable'))]
        policies = policies or load_policies(workspace, feature)
        if review and profile_name(policies) == 'high_risk' and not any(c['id'] == 'security' and c.get('required', True) for c in required):
            failures.append('required security command')
        if review and step_enabled(policies, 'implement-3-integrate') and not any(c['id'] == 'integration' and c.get('required', True) for c in required):
            failures.append('required integration command')
        if review:
            review_record = next((r for r in reversed(fresh) if r.get('kind') == 'review'), {})
            persona = policies.get('persona_mode') or {}
            independent = profile_name(policies) in ('standard', 'high_risk', 'full') or persona.get('fresh_subagent_per_persona')
            if review_record.get('disposition') != 'pass' or review_record.get('blocking_findings'):
                failures.append('fresh passing diff review')
            coder_sessions = review_record.get('coder_session_ids') or [review_record.get('coder_session_id')]
            if independent and (not all(coder_sessions) or not review_record.get('verifier_session_id') or review_record.get('verifier_session_id') in coder_sessions):
                failures.append('independent reviewer session')
            coder_models = review_record.get('coder_model_ids') or [review_record.get('coder_model_id')]
            if persona.get('verifier_different_model') and (not all(coder_models) or not review_record.get('verifier_model_id') or review_record.get('verifier_model_id') in coder_models):
                failures.append('different reviewer model')
        if approval and ((policies.get('autopilot') or {}).get('require_human_pr_approval') or policies.get('require_human_pr_approval')):
            latest_approval = next((r for r in reversed(fresh) if r.get('kind') == 'approval' and r.get('type') == 'pr_approval'), {})
            if latest_approval.get('decision') != 'approve' or not is_human_approver(latest_approval.get('approved_by')):
                failures.append('fresh local human approval record')
        return [{'id': 'completion_evidence', 'status': 'fail' if failures else 'pass', 'message': ', '.join(failures) or 'fresh checks and review'}]
    except (ValueError, TypeError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        return [{'id': 'completion_evidence', 'status': 'fail', 'message': str(exc)}]


def transition(workspace, feature, target):
    state = load_feature_state(workspace, feature)
    if not state:
        raise ValueError('canonical state missing')
    policies = load_policies(workspace, feature)
    current = state['current_step']
    if state.get('stage_status', {}).get('implement') == 'completed':
        raise ValueError('feature already completed; use audited repair to reopen')
    expected = 'completed' if current == 'implement-5-pr' else next_step_for_profile(policies, current)
    if target != expected or current == target:
        raise ValueError(f'expected next step {expected}, got {target}')
    if state['current_stage'] == 'specify' and target.split('-')[0] != 'specify' or target == 'implement-1-build' or target == 'completed':
        errors = profile_risk_errors(workspace, feature, policies)
        if errors:
            raise ValueError('; '.join(errors))
    before = fingerprint(workspace, feature)
    gates = []
    stage = state['current_stage']
    next_stage = target.split('-')[0] if target != 'completed' else stage
    if next_stage != stage:
        gates.append(stage + '-complete')
    if current in ('tasks-1-stories', 'tasks-2-code-spec'):
        gates.append(current + '-complete')
    if current.startswith('implement-'):
        gates.append('pr-ready' if target == 'completed' else current)
    for gate in gates:
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check-gates.py'), '--workspace', str(workspace), '--feature', feature, '--gate', gate], capture_output=True, text=True)
        result = json.loads(proc.stdout)
        if result.get('status') != 'pass':
            return {'status': 'error', 'error': 'gate_failed', 'gate': result}
    if fingerprint(workspace, feature) != before:
        raise ValueError('inputs changed during transition')
    statuses = dict(state['stage_status'])
    if next_stage != stage or target == 'completed':
        statuses[stage] = 'completed'
    stages = ['specify', 'plan', 'tasks', 'implement']
    for skipped in stages[stages.index(stage) + 1:stages.index(next_stage)]:
        statuses[skipped] = 'waived'
    if target != 'completed':
        statuses[next_stage] = 'in_progress'
    effective_step = current if target == 'completed' else target
    from lib.personas_load import get_persona_for_step
    fallback = 'analyst' if effective_step.startswith('specify-') or effective_step == 'tasks-1-stories' else 'architect' if effective_step.startswith('plan-') or effective_step == 'tasks-2-code-spec' else 'coder' if effective_step == 'implement-1-build' else 'tester'
    patch = {'stage_status': statuses, 'current_stage': next_stage, 'current_step': effective_step, 'persona': {'active': get_persona_for_step(effective_step) or fallback}}
    if next_stage == 'implement':
        patch['implement'] = {'current_substep': effective_step}
    result = set_feature_state(workspace, feature, patch=patch, operation='transition')
    if result['status'] == 'ok':
        append(workspace, feature, {'kind': 'transition', 'from': current, 'to': target, 'fingerprint': before})
    return result
