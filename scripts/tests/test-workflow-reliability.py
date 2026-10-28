"""Regression checks for the Alexa run's lifecycle and evidence failures."""
import builtins
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.completion_evidence import SHELL, run_checks
from lib.policies_load import load_policies, load_policies_file

spec = importlib.util.spec_from_file_location('gates', ROOT / 'scripts/check-gates.py')
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


class Reliability(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.feature = self.workspace / '.adlc5/demo'
        (self.feature / 'evidence').mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', self.temp.name], check=True)
        subprocess.run(['git', '-C', self.temp.name, '-c', 'user.name=Test', '-c',
                        'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'baseline'], check=True)
        self.state = {'schema_version': '3.0', 'feature': 'demo', 'current_stage': 'tasks',
                      'current_step': 'tasks-2-code-spec', 'tasks': {'stories': []},
                      'stage_status': {'specify': 'completed', 'plan': 'completed',
                                       'tasks': 'in_progress', 'implement': 'pending'}}
        self.save_state()
        self.policy = self.feature / 'policies.yaml'
        self.policy.write_text('autopilot:\n  profile: standard\n')

    def save_state(self):
        (self.feature / 'state.json').write_text(json.dumps(self.state))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/adlc5'), *args,
                               '--feature', 'demo', '--workspace', self.temp.name], capture_output=True, text=True)

    def test_empty_and_partial_acceptance_never_seal(self):
        for stories in ([], [{'id': 'US-1'}], [
            {'id': 'US-1', 'acceptance': [{'id': 'AC-1', 'owner': 'test',
                                        'evidence': {'type': 'command', 'value': 'true'}}]},
            {'id': 'US-2', 'acceptance': []},
        ]):
            self.state['tasks']['stories'] = stories
            self.save_state()
            original = (self.feature / 'state.json').read_bytes()
            result = self.cli('anchors', 'lock')
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('missing_acceptance', result.stdout)
            self.assertEqual((self.feature / 'state.json').read_bytes(), original)
            self.assertFalse((self.feature / 'acceptance-lock.json').exists())
            ref = subprocess.run(['git', '-C', self.temp.name, 'rev-parse', '--verify',
                                  'refs/adlc5/anchors/demo'], capture_output=True)
            self.assertNotEqual(ref.returncode, 0)

    def test_command_acceptance_can_be_locked(self):
        self.state['tasks']['stories'] = [{'id': 'US-1', 'acceptance': [
            {'id': 'AC-1', 'owner': 'test', 'evidence': {'type': 'command', 'value': 'true'}}]}]
        self.save_state()
        result = self.cli('anchors', 'lock')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.feature / 'acceptance-lock.json').exists())

    def test_tasks_gate_requires_each_story_acceptance(self):
        self.state['tasks']['stories'] = [{'id': 'US-1'}, {'id': 'US-2', 'acceptance': [{'id': 'AC-2'}]}]
        checks = gates.check_v2_tasks_stories_complete(self.workspace, 'demo', self.state)
        self.assertEqual([c['id'] for c in checks if c['status'] == 'fail'], ['acceptance_defined_US-1'])

    def test_duplicate_policy_keys_fail_with_both_parsers(self):
        self.policy.write_text('autopilot:\n  require_human_pr_approval: true\n  require_human_pr_approval: false\n')
        with self.assertRaisesRegex(ValueError, "duplicate YAML key 'require_human_pr_approval'.*lines 2 and 3"):
            load_policies_file(self.policy)
        real_import = builtins.__import__
        def without_yaml(name, *args, **kwargs):
            if name == 'yaml':
                raise ImportError('fixture: no PyYAML')
            return real_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=without_yaml):
            with self.assertRaisesRegex(ValueError, 'duplicate YAML key'):
                load_policies_file(self.policy)
            self.policy.write_text('autopilot:\n  profile: standard\ncustom_gates: {}\n')
            self.assertEqual(load_policies_file(self.policy)['custom_gates'], {})
            self.policy.write_text('autopilot: [unterminated')
            with self.assertRaises(ValueError):
                load_policies_file(self.policy)

    def test_malformed_policy_not_reinterpreted(self):
        self.policy.write_text('autopilot: [unterminated')
        with self.assertRaises(ValueError):
            load_policies_file(self.policy)

    def test_invalid_high_risk_policy_stops_before_commands(self):
        self.policy.write_text('autopilot:\n  profile: high_risk\n  require_human_pr_approval: false\n')
        with self.assertRaisesRegex(ValueError, 'high_risk requires'):
            load_policies(self.workspace, 'demo')
        (self.feature / 'evidence/checks.json').write_text(json.dumps([
            {'id': 'acceptance', 'command': 'touch should-not-run'}]))
        result = self.cli('evidence', 'check')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.workspace / 'should-not-run').exists())
        gate = self.cli('gate', '--gate', 'tasks-complete')
        self.assertNotEqual(gate.returncode, 0)
        self.assertIn('high_risk requires', json.loads(gate.stdout)['error'])
        pilot = self.cli('pilot')
        self.assertNotEqual(pilot.returncode, 0)
        self.assertEqual(json.loads(pilot.stdout)['stop_reason'], 'invalid_policy')
        self.assertFalse((self.feature / 'pilot/meta.json').exists())

    def test_passing_review_rejected_before_ingestion(self):
        self.state.update(current_stage='implement', current_step='implement-2-verify')
        self.save_state()
        self.policy.write_text('autopilot:\n  profile: standard\npersona_mode:\n  verifier_different_model: true\n')
        review = {'coder_session_id': 'coder', 'verifier_session_id': 'reviewer',
                  'coder_model_id': 'host default', 'verifier_model_id': 'unknown',
                  'disposition': 'pass', 'blocking_findings': []}
        request = self.feature / 'evidence/review-request.json'
        for changes in ({}, {'coder_model_id': 'model-a', 'verifier_model_id': 'model-a'},
                        {'coder_model_id': 'model-a', 'verifier_model_id': 'model-b', 'verifier_session_id': 'coder'}):
            request.write_text(json.dumps({**review, **changes}))
            result = self.cli('evidence', 'review', '--file', str(request))
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertFalse((self.feature / 'evidence/completion.jsonl').exists())
        request.write_text(json.dumps({**review, 'coder_model_id': 'model-a', 'verifier_model_id': 'model-b'}))
        result = self.cli('evidence', 'review', '--file', str(request))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len((self.feature / 'evidence/completion.jsonl').read_text().splitlines()), 1)

    def test_identical_success_reused_only_with_stable_inputs(self):
        real_run = subprocess.run
        for command, timeout, expected in [('true', 300, 1), ('exit 3', 300, 2),
                                           ('printf changed > changed.txt', 300, 2)]:
            checks = [{'id': 'acceptance', 'command': command, 'timeout_seconds': timeout},
                      {'id': 'integration', 'command': command, 'timeout_seconds': timeout}]
            (self.feature / 'evidence/checks.json').write_text(json.dumps(checks))
            with patch('lib.completion_evidence.subprocess.run', wraps=real_run) as runner:
                result = run_checks(self.workspace, 'demo')
                self.assertEqual(sum(c.args[0] == [SHELL, '-c', command] for c in runner.call_args_list), expected)
            self.assertGreaterEqual(result['duration_ms'], 0)
            if expected == 1:
                self.assertEqual(result['results'][1]['reused_from'], 'acceptance')
                self.assertEqual(result['results'][0]['output'], result['results'][1]['output'])
            else:
                self.assertNotIn('reused_from', result['results'][1])

    def test_timeout_difference_and_new_run_execute_again(self):
        (self.feature / 'evidence/checks.json').write_text(json.dumps([
            {'id': 'acceptance', 'command': 'true', 'timeout_seconds': 30},
            {'id': 'integration', 'command': 'true', 'timeout_seconds': 60}]))
        real_run = subprocess.run
        with patch('lib.completion_evidence.subprocess.run', wraps=real_run) as runner:
            run_checks(self.workspace, 'demo')
            run_checks(self.workspace, 'demo')
            self.assertEqual(sum(c.args[0] == [SHELL, '-c', 'true'] for c in runner.call_args_list), 4)

    def test_different_directories_are_not_reused(self):
        (self.workspace / 'nested').mkdir()
        (self.feature / 'evidence/checks.json').write_text(json.dumps([
            {'id': 'acceptance', 'command': 'true'},
            {'id': 'integration', 'command': 'true', 'cwd': 'nested'}]))
        real_run = subprocess.run
        with patch('lib.completion_evidence.subprocess.run', wraps=real_run) as runner:
            result = run_checks(self.workspace, 'demo')
            self.assertEqual(sum(c.args[0] == [SHELL, '-c', 'true'] for c in runner.call_args_list), 2)
        self.assertNotIn('reused_from', result['results'][1])

    def test_timed_out_commands_are_not_reused(self):
        (self.feature / 'evidence/checks.json').write_text(json.dumps([
            {'id': 'acceptance', 'command': 'true'},
            {'id': 'integration', 'command': 'true'}]))
        real_run = subprocess.run
        def timeout(command, *args, **kwargs):
            if command == [SHELL, '-c', 'true']:
                raise subprocess.TimeoutExpired(command, kwargs['timeout'])
            return real_run(command, *args, **kwargs)
        with patch('lib.completion_evidence.subprocess.run', side_effect=timeout) as runner:
            result = run_checks(self.workspace, 'demo')
            self.assertEqual(sum(c.args[0] == [SHELL, '-c', 'true'] for c in runner.call_args_list), 2)
        self.assertTrue(all(r['status'] == 'fail' for r in result['results']))
        self.assertNotIn('reused_from', result['results'][1])


if __name__ == '__main__':
    unittest.main()
