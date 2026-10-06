"""Run: python3 scripts/tests/test_completion_evidence.py"""
import json
import subprocess
import sys
import tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.completion_evidence import config, append, completion_checks, fingerprint, run_checks, transition
from lib.state_v2 import set_feature_state


def demo():
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        subprocess.run(['git', 'init', '-q', str(workspace)], check=True)
        subprocess.run(['git', '-C', str(workspace), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'baseline'], check=True)
        base = workspace / '.adlc5' / 'demo'
        (base / 'evidence').mkdir(parents=True)
        state = {'schema_version': '3.0', 'feature': 'demo', 'current_stage': 'specify', 'current_step': 'specify-0-git', 'stage_status': {'specify': 'in_progress', 'plan': 'pending', 'tasks': 'pending', 'implement': 'pending'}, 'tasks': {'stories': []}}
        (base / 'state.json').write_text(json.dumps(state))
        (base / 'policies.yaml').write_text('autopilot:\n  profile: tiny\n')
        checks = base / 'evidence/checks.json'
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'true'}]))
        assert set_feature_state(workspace, 'demo', patch={'current_step': 'implement-5-pr'})['error'] == 'protected_state'
        assert set_feature_state(workspace, 'demo', patch={'stage_status': {'implement': 'completed'}}, operation='repair')['error'] == 'repair_cannot_certify'
        original = (base / 'state.json').read_bytes()
        try:
            transition(workspace, 'demo', 'completed')
        except ValueError:
            pass
        else:
            raise AssertionError('jump permitted')
        assert (base / 'state.json').read_bytes() == original
        assert completion_checks(workspace, 'demo')[0]['status'] == 'fail'
        run_checks(workspace, 'demo')
        append(workspace, 'demo', {'kind': 'review', 'fingerprint': fingerprint(workspace, 'demo'), 'disposition': 'pass', 'blocking_findings': [], 'coder_session_id': 'a', 'verifier_session_id': 'b', 'coder_model_id': 'one', 'verifier_model_id': 'two'})
        assert completion_checks(workspace, 'demo')[0]['status'] == 'pass'
        # Ignored fallback policy changes and policy selection invalidate old evidence.
        (workspace / '.gitignore').write_text('.adlc5/\n')
        (base / 'policies.yaml').unlink()
        fallback = workspace / '.adlc5/policies.yaml'
        fallback.write_text('autopilot:\n  profile: tiny\n')
        run_checks(workspace, 'demo')
        append(workspace, 'demo', {'kind': 'review', 'fingerprint': fingerprint(workspace, 'demo'), 'disposition': 'pass', 'blocking_findings': []})
        assert completion_checks(workspace, 'demo')[0]['status'] == 'pass'
        before = fingerprint(workspace, 'demo')
        fallback.write_text('autopilot:\n  profile: standard\n')
        assert fingerprint(workspace, 'demo') != before
        assert completion_checks(workspace, 'demo')[0]['status'] == 'fail'
        before = fingerprint(workspace, 'demo')
        (base / 'policies.yaml').write_text(fallback.read_text())
        assert fingerprint(workspace, 'demo') != before
        (base / 'policies.yaml').write_text('autopilot:\n  profile: tiny\n')
        # Pass the configured timeout to the subprocess without a long test sleep.
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'true', 'timeout_seconds': 900}]))
        real_run = subprocess.run
        with patch('lib.completion_evidence.subprocess.run', wraps=real_run) as run:
            assert run_checks(workspace, 'demo')['results'][0]['status'] == 'pass'
            assert next(call.kwargs['timeout'] for call in run.call_args_list if call.kwargs.get('shell')) == 900
        for invalid in (0, -1, True, 1.5, '900', None):
            checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'true', 'timeout_seconds': invalid}]))
            try:
                config(workspace, 'demo')
            except ValueError:
                pass
            else:
                raise AssertionError(f'invalid timeout accepted: {invalid!r}')
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'true', 'timeout_seconds': 1}]))
        def timeout_command(*args, **kwargs):
            if kwargs.get('shell'):
                raise subprocess.TimeoutExpired(args[0], kwargs['timeout'])
            return real_run(*args, **kwargs)
        with patch('lib.completion_evidence.subprocess.run', side_effect=timeout_command):
            result = run_checks(workspace, 'demo')['results'][0]
            assert result['status'] == 'fail' and result['reason'] == 'timeout after 1 seconds'
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'true'}]))
        (workspace / 'untracked.py').write_text('broken = True\n')
        assert completion_checks(workspace, 'demo')[0]['status'] == 'fail'
        run_checks(workspace, 'demo')
        append(workspace, 'demo', {'kind': 'review', 'fingerprint': fingerprint(workspace, 'demo'), 'disposition': 'reject'})
        assert completion_checks(workspace, 'demo')[0]['status'] == 'fail'
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': None}]))
        assert run_checks(workspace, 'demo')['results'][0]['status'] == 'unsupported'
        assert completion_checks(workspace, 'demo')[0]['status'] == 'fail'
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'exit 3'}]))
        assert run_checks(workspace, 'demo')['results'][0]['exit_code'] == 3
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'printf changed > during-check.txt'}]))
        assert run_checks(workspace, 'demo')['stable'] is False
        # Explicit different-model policy applies to standard as well as high risk.
        policies = {'autopilot': {'profile': 'standard'}, 'persona_mode': {'verifier_different_model': True}}
        checks.write_text(json.dumps([{'id': 'acceptance', 'command': 'true'}]))
        run_checks(workspace, 'demo')
        append(workspace, 'demo', {'kind': 'review', 'fingerprint': fingerprint(workspace, 'demo'), 'disposition': 'pass', 'coder_session_id': 'a', 'verifier_session_id': 'b', 'coder_model_id': 'same', 'verifier_model_id': 'same'})
        assert 'different reviewer model' in completion_checks(workspace, 'demo', policies)[0]['message']
        # Metadata updates don't invalidate evidence; acceptance does.
        before = fingerprint(workspace, 'demo')
        state['scope'] = {'type': 'increment'}
        (base / 'state.json').write_text(json.dumps(state))
        assert fingerprint(workspace, 'demo') != before
    print('completion evidence checks passed')


if __name__ == '__main__':
    demo()
