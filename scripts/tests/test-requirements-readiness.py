"""Requirements evidence must fail closed independently of legacy clarity scores."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import requirements_readiness as readiness


class Readiness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.base = self.workspace / '.adlc5/demo'
        self.base.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', self.temp.name], check=True)
        subprocess.run(['git', '-C', self.temp.name, '-c', 'user.name=Test', '-c',
                        'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'baseline'], check=True)
        self.state = {'schema_version': '3.0', 'feature': 'demo', 'current_stage': 'specify',
                      'current_step': 'specify-4-handoff', 'git': {'isolation': 'current'},
                      'stage_status': {'specify': 'in_progress', 'plan': 'pending', 'tasks': 'pending', 'implement': 'pending'},
                      'clarity': {'score': 100}}
        self.save_state()
        (self.base / 'policies.yaml').write_text('autopilot:\n  profile: standard\n')
        (self.base / 'risk.json').write_text(json.dumps({'categories': [], 'uncertain': False, 'rationale': 'bounded fixture'}))
        (self.base / 'spec-handoff.md').write_text('# Behavior\nPreserve caller capitalization when trimming labels.\n# Acceptance\nMixed case labels retain their spelling.\n')

    def save_state(self):
        (self.base / 'state.json').write_text(json.dumps(self.state))

    def candidate(self):
        value = readiness.prepare(self.workspace, 'demo')
        value['requirements'] = [{'id': 'FR-1', 'source': '.adlc5/demo/spec-handoff.md',
                                  'acceptance': ['Given MiXeD, trimming preserves MiXeD.']}]
        value['review'] = {'author_session_id': 'author-1', 'reviewer_session_id': 'review-1',
                           'disposition': 'pass', 'coverage': ['behavior', 'contradictions', 'negative_cases', 'assumptions'],
                           'findings': []}
        return value

    def record(self, value=None):
        readiness.record(self.workspace, 'demo', value or self.candidate())

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/adlc5'), *args,
                               '--feature', 'demo', '--workspace', self.temp.name], capture_output=True, text=True)

    def test_clarity_padding_does_not_authorize_progression(self):
        (self.base / 'spec-handoff.md').write_text('# Functional Requirements\nTBD\n# Acceptance Criteria\nTBD\n# Non-functional Requirements\nTBD\nexample validation 200\n')
        lint = subprocess.run([sys.executable, str(ROOT / 'scripts/adlc5'), 'clarity',
                               str(self.base / 'spec-handoff.md')], capture_output=True, text=True, check=True)
        report = json.loads(lint.stdout)
        self.assertEqual(report['score'], 100)  # Preserved compatibility field is not readiness.
        self.assertTrue(report['heuristic'])
        self.assertFalse(report['gate_authority'])
        gate = self.cli('gate', '--gate', 'specify-complete')
        self.assertNotEqual(gate.returncode, 0)
        self.assertTrue(any(c['id'] == 'requirements_readiness' and c['status'] == 'fail'
                            for c in json.loads(gate.stdout)['checks']))
        before = (self.base / 'state.json').read_bytes()
        self.assertNotEqual(self.cli('transition', 'plan-4-design-discovery').returncode, 0)
        self.assertEqual(before, (self.base / 'state.json').read_bytes())
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            self.record()

    def test_concise_reviewed_intent_passes_without_score(self):
        self.state.pop('clarity')
        self.save_state()
        self.record()
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'pass')
        result = self.cli('transition', 'plan-4-design-discovery')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_stale_sources_scope_and_policy_block(self):
        self.record()
        path = self.base / 'spec-handoff.md'
        path.write_text(path.read_text() + '\nOnly administrators can export labels.\n')
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')
        self.record()
        self.state['scope'] = {'repo_profile': 'brownfield'}
        self.save_state()
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')
        self.record()
        (self.base / 'policies.yaml').write_text('autopilot:\n  profile: tiny\n')
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')

    def test_code_edits_do_not_require_a_new_intent_review(self):
        self.record()
        (self.workspace / 'app.py').write_text('value = 2\n')
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'pass')

    def test_review_changes_invalidate_completion_fingerprint(self):
        from lib.completion_evidence import fingerprint
        self.record()
        before = fingerprint(self.workspace, 'demo')
        value = self.candidate()
        value['review']['reviewer_session_id'] = 'another-review-session'
        self.record(value)
        self.assertNotEqual(before, fingerprint(self.workspace, 'demo'))

    def test_new_repository_rules_stale_review(self):
        self.record()
        (self.workspace / 'AGENTS.md').write_text('All exports require authorization.\n')
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')

    def test_additional_intent_sources_are_snapshotted_and_checked(self):
        path = self.workspace / 'product.md'
        path.write_text('# Product rule\nOnly administrators can export.\n')
        result = self.cli('readiness', 'prepare', '--source', 'product.md')
        self.assertEqual(result.returncode, 0, result.stdout)
        value = json.loads(result.stdout)
        completed = self.candidate()
        value.update(requirements=completed['requirements'], review=completed['review'])
        self.record(value)
        path.write_text('# Product rule\nAll users can export.\n')
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')

    def test_review_coverage_and_empty_sections_cannot_be_padded(self):
        value = self.candidate()
        value['review']['coverage'] = ['behavior'] * 4
        with self.assertRaises(ValueError):
            self.record(value)
        (self.base / 'spec-handoff.md').write_text('# Behavior\nTrim labels.\n# Acceptance\n')
        with self.assertRaisesRegex(ValueError, 'empty requirement section'):
            self.record()

    def test_open_and_contradictory_decisions_block(self):
        value = self.candidate()
        value['decisions'] = [{'id': 'D-1', 'requirement_ids': ['FR-1'], 'disposition': 'ask',
                               'status': 'open', 'blocking': True, 'rationale': 'Who owns export access?',
                               'evidence': [], 'revisit_when': 'authorization changes'}]
        with self.assertRaises(ValueError):
            self.record(value)
        value['decisions'][0].update(status='resolved', answer={'source': 'agent', 'text': 'Everyone'})
        with self.assertRaises(ValueError):
            self.record(value)
        value['decisions'][0]['answer']['source'] = 'user'
        value['review']['findings'] = [{'id': 'F-1', 'blocking': True, 'resolution': ''}]
        with self.assertRaises(ValueError):
            self.record(value)

    def test_invalid_records_preserve_previous_evidence(self):
        self.record()
        path = self.base / 'requirements-readiness.json'
        before = path.read_bytes()
        for change in ({'ready': True}, {'requirements': []}, {'schema_version': True}, {'review': []}):
            value = self.candidate()
            value.update(change)
            with self.assertRaises(ValueError):
                self.record(value)
            self.assertEqual(path.read_bytes(), before)

    def test_duplicates_missing_sources_and_escape_are_rejected(self):
        for mutate in (lambda x: x['requirements'].append(dict(x['requirements'][0])),
                       lambda x: x['sources'].clear(),
                       lambda x: x['sources'].append({'path': '../escape', 'sha256': '0' * 64})):
            value = self.candidate()
            mutate(value)
            with self.assertRaises(ValueError):
                self.record(value)
        outside = Path(self.temp.name).parent / 'outside-readiness'
        (self.workspace / 'external').symlink_to(outside)
        value = self.candidate()
        value['sources'].append({'path': 'external', 'sha256': '0' * 64})
        with self.assertRaises(ValueError):
            self.record(value)

    def test_high_risk_requires_independent_review(self):
        (self.base / 'policies.yaml').write_text('autopilot:\n  profile: high_risk\n  require_human_pr_approval: true\n')
        value = self.candidate()
        value['review']['reviewer_session_id'] = 'author-1'
        with self.assertRaisesRegex(ValueError, 'independent'):
            self.record(value)
        self.record()

    def test_cli_mcp_and_metadata_cannot_bypass_readiness(self):
        request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                              'params': {'name': 'adlc5_readiness', 'arguments': {
                                  'feature': 'demo', 'workspace': self.temp.name, 'action': 'prepare'}}})
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts/adlc5-mcp.py')],
                              input=request + '\n', capture_output=True, text=True, check=True)
        result = json.loads(json.loads(proc.stdout)['result']['content'][0]['text'])
        self.assertEqual(result['exit_code'], 0)
        # Metadata has no readiness authority even if its field is named ready.
        self.cli('state', 'set', '--patch', '{"readiness":{"ready":true}}')
        self.assertNotEqual(self.cli('readiness', 'check').returncode, 0)
        candidate = self.workspace / 'review-request.json'
        candidate.write_text(json.dumps(self.candidate()))
        self.assertEqual(self.cli('readiness', 'record', '--file', 'review-request.json').returncode, 0)
        self.assertEqual(self.cli('readiness', 'check').returncode, 0)
        for action in ('record', 'check', 'delivery', 'impact'):
            request_value = json.loads(request)
            arguments = request_value['params']['arguments']
            arguments['action'] = action
            if action == 'record':
                arguments['file'] = 'review-request.json'
            proc = subprocess.run([sys.executable, str(ROOT / 'scripts/adlc5-mcp.py')],
                                  input=json.dumps(request_value) + '\n', capture_output=True, text=True, check=True)
            result = json.loads(json.loads(proc.stdout)['result']['content'][0]['text'])
            self.assertEqual(result['exit_code'], 0, result)

    def test_duplicate_json_and_symlink_artifact_fail_closed(self):
        path = self.base / 'requirements-readiness.json'
        path.write_text('{"schema_version":1,"schema_version":1}')
        self.assertIn('duplicate', readiness.check(self.workspace, 'demo')['message'])
        path.unlink()
        target = self.workspace / 'target.json'
        target.write_text(json.dumps(self.candidate()))
        path.symlink_to(target)
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')

    def test_downstream_transition_and_gate_recheck_readiness(self):
        self.state.update(current_stage='plan', current_step='plan-1-engineering-architecture')
        self.save_state()
        before = (self.base / 'state.json').read_bytes()
        result = self.cli('transition', 'plan-2-engineering-patterns')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(before, (self.base / 'state.json').read_bytes())
        for gate in ('plan-complete', 'tasks-complete', 'implement-1-build', 'pr-ready'):
            result = self.cli('gate', '--gate', gate)
            self.assertTrue(any(c['id'] == 'requirements_readiness' and c['status'] == 'fail'
                                for c in json.loads(result.stdout)['checks']), gate)

    def test_legacy_completed_feature_remains_readable_without_auto_approval(self):
        self.state['stage_status']['implement'] = 'completed'
        self.save_state()
        before = (self.base / 'state.json').read_bytes()
        self.assertEqual(self.cli('state', 'get').returncode, 0)
        self.assertEqual(before, (self.base / 'state.json').read_bytes())
        self.assertFalse((self.base / 'requirements-readiness.json').exists())

    def test_malformed_canonical_state_fails_closed(self):
        (self.base / 'state.json').write_text('[1]')
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')
        result = self.cli('readiness', 'prepare')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['status'], 'error')

    def delivery(self):
        self.record()
        value = readiness.delivery_draft(self.workspace, 'demo')
        for item in value['delivery']['obligations']:
            item.update(status='non_applicable', rationale='Bounded string fixture has no such operational change.',
                        requirement_ids=[], method='')
        return value

    def test_plan_requires_operational_applicability_and_completion_requires_evidence(self):
        self.record()
        self.assertEqual(readiness.delivery_check(self.workspace, 'demo', 'plan')['status'], 'fail')
        value = self.delivery()
        item = next(o for o in value['delivery']['obligations'] if o['id'] == 'compatibility')
        item.update(status='pending', rationale='Existing callers consume labels.', requirement_ids=['FR-1'],
                    method='Exercise existing callers and mixed-case regression.')
        self.record(value)
        self.assertEqual(readiness.delivery_check(self.workspace, 'demo', 'plan')['status'], 'pass')
        self.assertEqual(readiness.delivery_check(self.workspace, 'demo', 'complete')['status'], 'fail')
        item['status'] = 'satisfied'
        with self.assertRaisesRegex(ValueError, 'require evidence'):
            self.record(value)
        item['evidence'] = [readiness.source(self.workspace, '.adlc5/demo/spec-handoff.md')]
        self.record(value)
        self.assertEqual(readiness.delivery_check(self.workspace, 'demo', 'complete')['status'], 'fail')

    def test_traceability_requires_all_requirements_and_matching_acceptance(self):
        self.state['tasks'] = {'stories': [{'id': 'US-1', 'status': 'pending'}]}
        self.save_state()
        value = self.delivery()
        self.record(value)
        self.assertEqual(readiness.delivery_check(self.workspace, 'demo', 'tasks')['status'], 'fail')
        spec = self.base / 'tasks/code-spec/US-1.md'
        spec.parent.mkdir(parents=True)
        spec.write_text('---\nstory_id: US-1\nacceptance_criteria: [AC-1]\n---\nPreserve case.\n')
        value['delivery']['traceability'] = [{'story_id': 'US-1', 'requirement_ids': ['FR-1'],
                                             'decision_ids': [], 'acceptance_criteria': ['AC-1']}]
        self.record(value)
        self.assertEqual(readiness.delivery_check(self.workspace, 'demo', 'tasks')['status'], 'pass')
        spec.write_text(spec.read_text().replace('AC-1', 'AC-2'))
        self.assertEqual(readiness.delivery_check(self.workspace, 'demo', 'tasks')['status'], 'fail')

    def test_changed_intent_reports_impact_and_preserves_prior_review(self):
        self.record()
        previous = self.candidate()
        (self.base / 'spec-handoff.md').write_text('# Behavior\nRequire administrator permission for exports.\n')
        report = readiness.impact(self.workspace, 'demo')
        self.assertEqual(report['status'], 'stale')
        self.assertEqual(report['affected_requirements'], ['FR-1'])
        self.record()
        history = self.base / 'evidence/readiness-history' / (readiness.digest(previous) + '.json')
        self.assertEqual(readiness.load_record(history), previous)

    def product_question(self):
        from runner.questions import pending, intent
        return pending(self.workspace, 'demo', {'question': {
            'decision_id': 'D-1', 'category': 'product', 'text': 'Who may export?',
            'rationale': 'Exports expose tenant records.', 'recommendation': 'Administrators only.',
            'alternatives': ['All tenant members.'], 'requirement_ids': ['FR-1'],
            'intent_sha256': intent(self.workspace, 'demo')}}, 'q1', 'specify-2-requirements', 'test')

    def test_product_answer_is_retained_once_and_never_authorizes_commands(self):
        from runner.questions import current_answers
        from runner.answer import record_reply
        self.record()
        question = self.product_question()
        path = self.base / 'pilot/pending-question.json'
        path.parent.mkdir()
        path.write_text(json.dumps(question))
        self.assertEqual(record_reply(self.workspace, path, 'yes', 'q1'), 0)
        self.assertEqual(record_reply(self.workspace, path, 'yes', 'q1'), 0)
        self.assertEqual(record_reply(self.workspace, path, 'no', 'q1'), 2)
        self.assertEqual(len(current_answers(self.workspace, 'demo')), 1)
        self.assertFalse((path.parent / 'approved-commands.json').exists())
        with self.assertRaisesRegex(ValueError, 'already answered'):
            self.product_question()
        question['denied_actions'] = [{'tool_name': 'Bash', 'tool_input': {'command': 'publish'}}]
        path.write_text(json.dumps(question))
        self.assertEqual(record_reply(self.workspace, path, 'yes', 'q1'), 2)

    def test_stale_product_answers_are_not_consumed(self):
        from runner.questions import current_answers
        from runner.answer import record_reply
        self.record()
        path = self.base / 'pilot/pending-question.json'
        path.parent.mkdir()
        path.write_text(json.dumps(self.product_question()))
        (self.base / 'spec-handoff.md').write_text('# Behavior\nExport only archived labels.\n')
        self.assertEqual(record_reply(self.workspace, path, 'yes', 'q1'), 2)
        self.assertFalse((path.parent / 'answers.jsonl').exists())
        self.assertEqual(current_answers(self.workspace, 'demo'), [])

    def test_answer_journal_recovers_after_interrupted_write(self):
        from unittest.mock import patch
        from runner.answer import record_reply
        self.record()
        path = self.base / 'pilot/pending-question.json'
        path.parent.mkdir()
        path.write_text(json.dumps(self.product_question()))
        from lib.state_v2 import atomic_write_text
        def interrupt_journal(target, content):
            if target.name == 'answers.jsonl':
                raise OSError('interrupted')
            return atomic_write_text(target, content)
        with patch('lib.state_v2.atomic_write_text', side_effect=interrupt_journal):
            with self.assertRaises(OSError):
                record_reply(self.workspace, path, 'Administrators only.', 'q1')
        self.assertEqual(json.loads(path.read_text())['answer'], 'Administrators only.')
        from runner.run import resume_question
        self.assertIsNone(resume_question(self.workspace, 'demo'))
        self.assertFalse(path.exists())
        self.assertTrue((path.parent / 'answered-questions/q1.json').is_file())
        self.assertEqual(len((path.parent / 'answers.jsonl').read_text().splitlines()), 1)
        self.assertIsNone(resume_question(self.workspace, 'demo'))

    def test_permission_approval_is_bound_to_current_inputs(self):
        from runner.questions import pending
        from runner.answer import record_reply
        self.record()
        question = pending(self.workspace, 'demo', {'question': 'Allow the test command?',
            'denied_actions': [{'tool_name': 'Bash', 'tool_input': {'command': 'python3 test_app.py'}}]},
            'permission-1', 'implement-1-build', 'test')
        path = self.base / 'pilot/pending-question.json'
        path.parent.mkdir()
        path.write_text(json.dumps(question))
        (self.workspace / 'app.py').write_text('changed = True\n')
        self.assertEqual(record_reply(self.workspace, path, 'allow', 'permission-1'), 2)
        self.assertFalse((path.parent / 'approved-commands.json').exists())

    def test_resume_archives_stale_product_questions_without_consuming_answers(self):
        from runner.run import resume_question
        self.record()
        path = self.base / 'pilot/pending-question.json'
        path.parent.mkdir()
        path.write_text(json.dumps(self.product_question()))
        (self.base / 'spec-handoff.md').write_text('# Behavior\nExport only archived items.\n')
        self.assertIsNone(resume_question(self.workspace, 'demo'))
        self.assertTrue((path.parent / 'superseded-questions/q1.json').is_file())
        self.assertFalse((path.parent / 'answers.jsonl').exists())
        path.write_text('{broken')
        with self.assertRaisesRegex(RuntimeError, 'invalid pending'):
            resume_question(self.workspace, 'demo')

    def test_legacy_answers_remain_context_and_are_not_current_authority(self):
        from runner.questions import current_answers
        path = self.base / 'pilot/answers.jsonl'
        path.parent.mkdir()
        path.write_text(json.dumps({'id': 'old', 'answer': 'Keep current ordering.'}) + '\n')
        answers = current_answers(self.workspace, 'demo')
        self.assertEqual(len(answers), 1)
        self.assertTrue(answers[0]['legacy_unbound'])

    def test_declared_risk_cannot_waive_corresponding_operational_obligation(self):
        (self.base / 'policies.yaml').write_text('autopilot:\n  profile: high_risk\n  require_human_pr_approval: true\n')
        (self.base / 'risk.json').write_text(json.dumps({'categories': ['auth'], 'uncertain': False,
                                                      'rationale': 'Exports expose tenant records.'}))
        value = self.delivery()
        with self.assertRaisesRegex(ValueError, 'declared risk'):
            self.record(value)

    def test_constraint_and_conformance_evidence_stales_after_implementation_changes(self):
        value = self.delivery()
        implementation = self.workspace / 'app.py'
        implementation.write_text('def label(value): return value.strip()\n')
        value['delivery']['constraints'] = [{'requirement_ids': ['FR-1'], 'text': 'Preserve caller capitalization.',
            'source': readiness.source(self.workspace, '.adlc5/demo/spec-handoff.md')}]
        value['delivery']['conformance'] = {'reviewer_session_id': 'review-1',
            'coverage': ['missing', 'partial', 'contradictory', 'unrequested', 'constraints'],
            'requirements': ['FR-1'], 'evidence': [readiness.source(self.workspace, 'app.py')]}
        self.record(value)
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'pass')
        implementation.write_text('def label(value): return value.title()\n')
        self.assertEqual(readiness.check(self.workspace, 'demo')['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
