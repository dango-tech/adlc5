"""Four-host archives, self-install plans, provenance and preservation contracts."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('install_plugin', ROOT / 'scripts/install-plugin.py')
installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.output.cleanup)
        cls.out = Path(cls.output.name)
        subprocess.run([sys.executable, str(ROOT / 'scripts/package-plugin.py'), '--out', str(cls.out)], check=True, capture_output=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        env = patch.dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        env.start(); self.addCleanup(env.stop)

    def test_four_host_archives_checksums_and_provenance(self):
        sums = (self.out / 'SHA256SUMS').read_text().splitlines()
        self.assertEqual(len(sums), 8)
        for line in sums:
            checksum, name = line.split('  ')
            self.assertEqual(hashlib.sha256((self.out / name).read_bytes()).hexdigest(), checksum)
        for host, label in (('codex', 'codex'), ('claude', 'claude-code'), ('cursor', 'cursor'), ('hermes', 'hermes')):
            archive = next(self.out.glob('adlc5-' + label + '-plugin-*.zip'))
            with zipfile.ZipFile(archive) as bundle:
                self.assertIn('install.py', bundle.namelist())
                self.assertIn('scripts/install-plugin.py', bundle.namelist())
                metadata = json.loads(bundle.read('INSTALL.json'))
                self.assertEqual(metadata['host'], host)
                self.assertEqual(len(metadata['source_revision']), 40)
                if host == 'hermes':
                    self.assertIn('mcp.json', bundle.namelist())
                    self.assertNotIn('.codex-plugin/plugin.json', bundle.namelist())

    def test_all_dry_runs_are_read_only(self):
        for host in ('codex', 'claude', 'cursor', 'hermes'):
            result = installer.install(self.out / host / 'adlc5', True)
            self.assertEqual(result['status'], 'dry-run')
            wrapped = subprocess.run([sys.executable, str(self.out / host / 'adlc5/install.py'), '--dry-run'], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(wrapped.stdout)['host'], host)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_codex_prepares_supported_marketplace_without_fake_install(self):
        with patch.object(installer.shutil, 'which', return_value='/example/codex'), patch.object(installer.subprocess, 'run') as run:
            result = installer.install(self.out / 'codex/adlc5')
        self.assertEqual(result['status'], 'prepared')
        self.assertEqual(run.call_args.args[0][1:4], ['plugin', 'marketplace', 'add'])
        self.assertTrue((Path(result['source']).parent / 'marketplace/.agents/plugins/marketplace.json').is_file())

    def test_hermes_uses_native_git_source_and_does_not_enable_or_bypass_scan(self):
        with patch.object(installer.shutil, 'which', return_value='/example/tool'), patch.object(installer.subprocess, 'run') as run:
            installer.install(self.out / 'hermes/adlc5')
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ['hermes', 'plugins', 'install'])
        self.assertTrue(command[3].startswith('file://'))
        self.assertEqual(command[-1], '--no-enable')
        self.assertNotIn('--force', command)

    def test_cursor_refuses_unknown_destination_and_preserves_managed_backup(self):
        target = self.home / '.cursor/plugins/local/adlc5'
        target.mkdir(parents=True)
        (target / 'user.txt').write_text('preserve me')
        with self.assertRaises(ValueError): installer.install(self.out / 'cursor/adlc5')
        self.assertEqual((target / 'user.txt').read_text(), 'preserve me')
        (target / '.adlc5-package.json').write_text('{"name":"adlc5"}')
        result = installer.install(self.out / 'cursor/adlc5')
        self.assertEqual((Path(result['backup']) / 'user.txt').read_text(), 'preserve me')
        self.assertTrue((target / '.cursor-plugin/plugin.json').is_file())

    def test_package_symlink_is_refused(self):
        source = self.home / 'package'
        source.mkdir()
        (source / 'INSTALL.json').write_text('{"host":"cursor","version":"5.1.0"}')
        (source / 'outside').symlink_to(self.out / 'cursor/adlc5/README.md')
        with self.assertRaises(ValueError): installer.install(source, True)


if __name__ == '__main__': unittest.main()
