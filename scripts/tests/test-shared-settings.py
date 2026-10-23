"""Shared config authority, privacy and content-addressed runtime contracts."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.config_layers import config_paths, effective_config, project_identity
from lib.pulse_settings import snapshot
from lib.model_routing import merge_model_config


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.repo = self.root / 'repo'
        self.home.mkdir(); self.repo.mkdir()
        env = patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        env.start(); self.addCleanup(env.stop)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def test_explicit_worktree_project_machine_and_enforced_precedence(self):
        paths = dict(config_paths(self.repo))
        self.write(paths['master'], {'defaults': {'summary': 'brief'}, 'enforced': {'platform_modes': {'hermes': 'confined'}}})
        self.write(paths['project'], {'defaults': {'summary': 'detailed'}})
        self.write(paths['worktree'], {'defaults': {'summary': 'off'}, 'platform_modes': {'hermes': 'attended'}})
        values, rows = effective_config(self.repo)
        self.assertEqual(values['defaults']['summary'], 'off')
        self.assertEqual(values['platform_modes']['hermes'], 'confined')
        self.assertEqual(effective_config(self.repo, scope='project')[0]['defaults']['summary'], 'detailed')
        self.assertEqual(effective_config(self.repo, {'defaults': {'summary': 'brief'}})[0]['defaults']['summary'], 'brief')
        with self.assertRaises(ValueError):
            effective_config(self.repo, {'platform_modes': {'hermes': 'attended'}})
        self.assertEqual(merge_model_config(ROOT, self.repo), values)
        self.assertEqual(next(r for r in rows if r['key'] == 'platform_modes.hermes')['status'], 'enforced')

    def test_secrets_and_invalid_config_do_not_leak_or_become_defaults(self):
        paths = dict(config_paths(self.repo))
        self.write(paths['master'], {'api_key': 'SECRET-VALUE', 'platform_profiles': {'codex': {'execution': {'model': 'sk-project-private'}}}})
        report = json.dumps(snapshot(self.repo))
        self.assertNotIn('SECRET-VALUE', report)
        self.assertNotIn('sk-project-private', report)
        paths['master'].write_text('bad: [unterminated')
        with self.assertRaises(ValueError): effective_config(self.repo)
        self.assertTrue(snapshot(self.repo)['error'])
        self.assertEqual(snapshot(self.repo)['rows'], [])

    def test_git_worktrees_share_project_but_keep_local_overrides(self):
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        other = self.root / 'other'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '--detach', str(other)], check=True, capture_output=True)
        self.assertEqual(project_identity(self.repo), project_identity(other))
        self.assertEqual(dict(config_paths(self.repo))['project'], dict(config_paths(other))['project'])
        self.assertNotEqual(dict(config_paths(self.repo))['worktree'], dict(config_paths(other))['worktree'])

    def test_cache_cannot_override_execution(self):
        self.write(self.repo / '.agent-cache/config.json', {'default_host': 'attacker'})
        self.write(self.repo / '.adlc5/pulse/workspace.json', {'default_host': 'attacker'})
        self.assertNotIn('default_host', effective_config(self.repo)[0])

    def test_shared_runtime_reuses_content_and_refuses_mutation(self):
        spec = importlib.util.spec_from_file_location('shared_home', ROOT / 'scripts/shared-home.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        first = module.stage(ROOT)
        self.assertEqual(module.stage(ROOT), first)
        self.assertFalse((first / 'config.yaml').exists())
        self.assertFalse((first / 'scripts/tests').exists())
        self.assertTrue((first / '.adlc5-package.json').exists())
        self.assertEqual(json.loads((self.home / '.adlc5/runtime.json').read_text())['path'], str(first))
        (first / 'core/VERSION').write_text('modified')
        with self.assertRaises(ValueError): module.stage(ROOT)


if __name__ == '__main__': unittest.main()
