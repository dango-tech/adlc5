"""Dependency closure and unknown-change fallback for CI selection."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('ci_plan', Path(__file__).resolve().parents[1] / 'ci-plan.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PlanTests(unittest.TestCase):
    def test_docs_do_not_run_runtime(self):
        data = module.plan(['docs/pulse.md'])
        self.assertTrue(data['docs'])
        self.assertFalse(data['full'])

    def test_storage_has_platform_install_and_package_closure(self):
        data = module.plan(['scripts/pulse.py'])
        self.assertTrue(all(data[key] for key in ('pulse', 'platforms', 'install', 'packages')))

    def test_shared_unknown_and_empty_fail_to_full(self):
        for paths in ([], ['core/gates.yaml'], ['scripts/lib/config_layers.py'], ['.github/workflows/ci.yml'], ['future/subsystem.py']):
            self.assertTrue(module.plan(paths)['full'])

    def test_mixed_pr_unions_suites(self):
        data = module.plan(['shared/pulse/board.js', 'telemetry-intake/index.mjs'])
        self.assertTrue(all(data[key] for key in ('pulse', 'packages', 'telemetry')))

    def test_known_runner_changes_select_integration_contracts(self):
        data = module.plan(['scripts/runner/answer.py'])
        self.assertTrue(data['runner'] and data['packages'])
        self.assertFalse(data['full'])

    def test_required_gate_rejects_skipped_cancelled_and_missing_plan(self):
        flags = {key: str(value).lower() for key, value in module.plan(['shared/pulse/board.js']).items() if key != 'reasons'}
        jobs = {name: {'result': 'success'} for name in ('privacy', 'windows', 'pulse', 'packages')}
        jobs['changes'] = {'result': 'success', 'outputs': flags}
        module.check_results(jobs)
        for status in ('skipped', 'cancelled', 'failure'):
            jobs['pulse']['result'] = status
            with self.assertRaises(ValueError): module.check_results(jobs)
        jobs['pulse']['result'] = 'success'
        jobs['changes']['outputs'] = {}
        with self.assertRaises(ValueError): module.check_results(jobs)


if __name__ == '__main__':
    unittest.main()
