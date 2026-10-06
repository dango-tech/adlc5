#!/usr/bin/env python3
"""Disposable pilot smoke: real frozen checks fail before delivery; unknown is not success."""
import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'scripts/evaluation/run-case.py'


class Pilot(unittest.TestCase):
    def test_outcome_types_fail_closed(self):
        spec = importlib.util.spec_from_file_location('scorer', ROOT / 'scripts/evaluate-runs.py')
        scorer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scorer)
        good = dict(anchors_passed=True, regression_passed=True, quality_gates_passed=True,
                    anchor_changed=False, rework=0, human_rejected=False, escaped_defects=0)
        self.assertTrue(scorer.successful(good))
        for field in good:
            values = [None, '0', [], {}]
            values += [True, False, -1, float('inf'), 0.0] if field in ('rework', 'escaped_defects') else [0, 1]
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assertFalse(scorer.successful(dict(good, **{field: value})))
        telemetry = [{'run_id': 'r', 'node_id': 'n'}]
        usage = [{'run_id': 'r', 'node_id': 'n', 'tokens': {'total': 1}}]
        unknown = dict(good, run_id='r', rework=None)
        report = scorer.evaluate(telemetry, usage, [unknown])
        self.assertEqual(report['runs']['successful'], 0)
        self.assertEqual(report['missing']['outcomes_incomplete'], 1)

    def test_six_frozen_cases_and_unknown_results(self):
        bank = json.loads((ROOT / 'templates/evaluation/cases.json').read_text())
        self.assertEqual(len(bank['cases']), 6)
        with tempfile.TemporaryDirectory() as tmp:
            for case in bank['cases']:
                run = Path(tmp) / case['case_id']
                subprocess.run([sys.executable, str(RUNNER), 'prepare', '--case', case['case_id'], '--arm', 'baseline', '--host', 'test-only', '--model', 'none', '--directory', str(run)], check=True, capture_output=True)
                result = subprocess.run([sys.executable, str(RUNNER), 'collect', '--directory', str(run)], check=True, capture_output=True, text=True)
                report = json.loads(result.stdout)
                self.assertNotEqual(report['consumer_checks']['acceptance']['exit_code'], 0, case['case_id'])
                self.assertEqual(report['consumer_checks']['regression']['exit_code'], 0)
                self.assertEqual(report['runs']['successful'], 0)
                self.assertFalse(report['accounting_available'])
                self.assertIsNone(json.loads((run / 'outcomes.jsonl').read_text())['escaped_defects'])
                # Frozen acceptance changes must be detected even if someone edits the test.
                (run / 'acceptance.py').write_text('pass\n')
                subprocess.run([sys.executable, str(RUNNER), 'collect', '--directory', str(run)], check=True, capture_output=True)
                self.assertTrue(json.loads((run / 'outcomes.jsonl').read_text())['anchor_changed'])
                (run / 'manifest.json').write_text('{}')
                rejected = subprocess.run([sys.executable, str(RUNNER), 'collect', '--directory', str(run)], capture_output=True)
                self.assertEqual(rejected.returncode, 2)

    def test_scripted_kernel_delivery_and_process_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/evaluation/demo-consumer.py'), '--directory', str(Path(tmp) / 'demo')], check=True, capture_output=True, text=True)
            report = json.loads(result.stdout)
            self.assertTrue(report['checks_passed'])
            self.assertTrue(report['invalid_completion_rejected'])
            self.assertTrue(report['completion_without_review_blocked'])
            self.assertFalse(report['live_agent_delivery'])
            self.assertFalse(report['human_approval_recorded'])

    def test_baseline_is_materialized_from_frozen_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'baseline'
            subprocess.run([sys.executable, str(RUNNER), 'prepare', '--case', 'tiny-label', '--arm', 'baseline', '--host', 'test-only', '--model', 'none', '--directory', str(run)], check=True, capture_output=True)
            self.assertEqual((run / 'framework/core/VERSION').read_text(), subprocess.check_output(['git', 'show', json.loads((ROOT / 'templates/evaluation/cases.json').read_text())['baseline_framework_revision'] + ':core/VERSION'], cwd=ROOT, text=True))
            self.assertFalse(json.loads((run / 'manifest.json').read_text())['framework_dirty'])
            (run / 'framework/core/VERSION').write_text('changed')
            result = subprocess.run([sys.executable, str(RUNNER), 'collect', '--directory', str(run)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('framework changed', result.stderr)


if __name__ == '__main__':
    unittest.main()
