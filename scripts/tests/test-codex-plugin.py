"""Codex archive metadata preservation and relocated local MCP contracts."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]


class CodexPluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='adlc5-codex-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name).resolve()
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/package-plugin.py'),
                                 '--host', 'codex', '--out', str(cls.work / 'dist')],
                                capture_output=True, text=True, check=True)
        cls.info = json.loads(result.stdout)
        cls.package = cls.work / 'relocated package'
        with zipfile.ZipFile(cls.info['packages']['codex']['zip']) as archive:
            archive.extractall(cls.package)
            for member in archive.infolist():
                (cls.package / member.filename).chmod(member.external_attr >> 16)
        cls.consumer = cls.work / 'consumer repo'
        cls.consumer.mkdir()
        subprocess.run(['git', 'init', '-q', str(cls.consumer)], check=True)

    def call(self, name, arguments):
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                   'params': {'name': name, 'arguments': arguments}}
        result = subprocess.run([sys.executable, str(self.package / 'scripts/adlc5-mcp.py')],
                                input=json.dumps(request)+'\n', capture_output=True, text=True,
                                cwd=self.consumer, check=True, timeout=60,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        return json.loads(result.stdout)['result']

    def test_listing_and_review_metadata_survive_build(self):
        source = json.loads((ROOT / 'plugin.json').read_text())
        built = json.loads((self.package / 'plugin.json').read_text())
        self.assertEqual(source['extensions'], built['extensions'])
        extension = built['extensions']['com.openai']
        compat = json.loads((self.package / '.codex-plugin/plugin.json').read_text())
        listing = extension['interface']
        self.assertEqual(compat['interface'], listing)
        self.assertEqual(compat['extensions']['com.openai']['review'], extension['review'])
        self.assertTrue(extension['requires_local_executor'])
        self.assertLessEqual(len(listing['shortDescription']), 30)
        self.assertEqual(listing['category'], 'Developer Tools')
        self.assertEqual(len(extension['review']['test_cases']['positive']), 5)
        self.assertEqual(len(extension['review']['test_cases']['negative']), 3)
        self.assertFalse(extension['review']['commerce'])
        self.assertEqual(extension['publication']['countries'], [])
        for field in ('logo', 'composerIcon'):
            data = (self.package / listing[field]).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            width, height = struct.unpack('>II', data[16:24])
            self.assertEqual(width, height)
            self.assertGreaterEqual(width, 256 if field == 'logo' else 48)
            self.assertLessEqual(len(data), 5*1024*1024)
        for path in self.package.rglob('*.json'):
            value = json.loads(path.read_text())
            if path.name == 'plugin.json':
                self.assertIsNone(value.get('apps'))
                self.assertIsNone(value.get('extensions', {}).get('com.openai', {}).get('apps'))
        self.assertFalse((self.package / '.app.json').exists())
        self.assertFalse((self.package / '.claude-plugin').exists())
        self.assertFalse((self.package / '.cursor-plugin').exists())

    def test_relocated_stdio_protocol_and_annotations(self):
        requests = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25'}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
        ]
        result = subprocess.run([sys.executable, str(self.package / 'scripts/adlc5-mcp.py')],
                                input=''.join(json.dumps(r)+'\n' for r in requests),
                                capture_output=True, text=True, cwd=self.consumer, check=True)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]['result']['protocolVersion'], '2025-11-25')
        tools = replies[1]['result']['tools']
        for tool in tools:
            for hint in ('readOnlyHint', 'openWorldHint', 'destructiveHint'):
                self.assertIsInstance(tool['annotations'][hint], bool, (tool['name'], hint))
        self.assertTrue(next(t for t in tools if t['name'] == 'adlc5_state_get')['annotations']['readOnlyHint'])
        self.assertFalse(next(t for t in tools if t['name'] == 'adlc5_evidence')['annotations']['readOnlyHint'])
        result = self.call('adlc5_version', {})
        self.assertFalse(result['isError'])
        payload = json.loads(result['content'][0]['text'])
        self.assertEqual(payload['stdout'].strip(), 'adlc5 '+self.info['version'])

    def test_pulse_missing_state_and_invalid_arguments(self):
        args = {'workspace': str(self.consumer)}
        self.assertFalse(self.call('adlc5_pulse', args)['isError'])
        self.assertTrue(self.call('adlc5_state_get', {**args, 'feature': 'missing'})['isError'])
        self.assertTrue(self.call('adlc5_state_get', {**args, 'feature': '../outside'})['isError'])
        self.assertTrue(self.call('adlc5_version', {'unexpected': True})['isError'])

    def test_review_fixtures_from_consumer_setup(self):
        home = self.work / 'isolated home'
        home.mkdir()
        env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home)}
        for script, args in (
            ('plugin-setup.sh', ['--host', 'codex', '--project', str(self.consumer)]),
            ('init-feature.sh', ['--feature', 'submission-demo', '--workspace', str(self.consumer)]),
        ):
            subprocess.run(['bash', str(self.package / 'scripts' / script), *args],
                           cwd=self.consumer, env=env, capture_output=True, text=True,
                           check=True, timeout=60)
        state = self.call('adlc5_state_get', {'feature': 'submission-demo', 'workspace': str(self.consumer)})
        self.assertFalse(state['isError'])
        payload = json.loads(state['content'][0]['text'])
        self.assertEqual(json.loads(payload['stdout'])['current_stage'], 'specify')
        (self.consumer / 'spec.md').write_text('# Export status\nPrint a local JSON report without changing workflow state.\n')
        clarity = self.call('adlc5_clarity', {'file_path': 'spec.md', 'workspace': str(self.consumer)})
        self.assertFalse(clarity['isError'])
        report = json.loads(json.loads(clarity['content'][0]['text'])['stdout'])
        self.assertTrue(report['heuristic'])
        self.assertFalse(report['gate_authority'])
        unindexed = self.work / 'unindexed repo'
        unindexed.mkdir()
        subprocess.run(['git', 'init', '-q', str(unindexed)], check=True)
        index = self.call('adlc5_repo_index', {'action': 'check', 'workspace': str(unindexed)})
        self.assertTrue(index['isError'])
        report = json.loads(json.loads(index['content'][0]['text'])['stdout'])
        self.assertEqual(report['reason'], 'missing cache')


if __name__ == '__main__':
    unittest.main()
