"""Global Pulse discovery, attribution and local-only rendering contracts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.pulse_fleet import collect, discover, sessions
from lib.pulse import board_document


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_overlapping_roots_worktrees_archives_and_missing_usage(self):
        workspace = self.root / 'repo'
        active = workspace / '.adlc5/export'
        archived = workspace / '.adlc5/_archive/old-20260101'
        ignored = workspace / 'node_modules/pkg/.adlc5/hidden'
        for directory in (active, archived, ignored):
            directory.mkdir(parents=True)
        (active / 'state.json').write_text(json.dumps({'schema_version': '3.0', 'feature': 'export',
            'current_stage': 'specify', 'current_step': 'specify-2-requirements'}))
        (archived / 'FEATURE.md').write_text('# Old feature\nHistorical evidence only.\n')
        (workspace / '.adlc5/README.md').write_text('# Workspace\n')
        (workspace / '.adlc5/_archive/index.md').write_text('# Archive\n')
        warnings = []
        self.assertEqual(discover([self.root, workspace], warnings), [workspace.resolve()])
        data = collect([self.root, workspace], [])
        self.assertEqual(data['fleet']['workspaces'], 1)
        self.assertEqual(len(data['features']), 2)
        self.assertFalse(any('unsafe_' in warning for warning in data['warnings']))
        self.assertEqual(len({f['identity'] for f in data['features']}), 2)
        self.assertTrue(all(f['usage']['known_cost_usd'] is None for f in data['features']))
        self.assertTrue(any(f['archive_id'] == 'old-20260101' for f in data['features']))
        page = board_document(data)
        self.assertIn('Your ADLC5 activity', page)
        self.assertIn("connect-src 'none'", page)
        self.assertNotIn('https://', page)

    def test_transcripts_require_explicit_evidence_and_do_not_export_prompt_text(self):
        directory = self.root / 'sessions'
        directory.mkdir()
        (directory / 'one.jsonl').write_text('\n'.join(json.dumps(row) for row in [
            {'type': 'session_meta', 'payload': {'id': 'one', 'cwd': '/example/repo'}},
            {'type': 'response_item', 'timestamp': '2026-10-23T01:00:00Z', 'payload': {'type': 'message',
                'role': 'assistant', 'content': [{'type': 'text', 'text': '@adlc5 skill catalog SECRET-PROMPT'}]}},
            {'type': 'response_item', 'timestamp': '2026-10-23T02:00:00Z', 'payload': {'type': 'function_call',
                'name': 'exec_command', 'arguments': '{"cmd":"scripts/adlc5 transition tasks-1-stories --feature export"}'}},
            {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage':
                {'input_tokens': 100, 'cached_input_tokens': 80, 'output_tokens': 20}}}},
        ]))
        # Same session in a copied transcript remains one row, not two runs.
        (directory / 'copy.jsonl').write_text((directory / 'one.jsonl').read_text())
        warnings = []
        rows, files = sessions([('codex', directory)], warnings)
        self.assertEqual(files, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['tokens'], 120)  # Cached input is already inside input.
        self.assertIsNone(rows[0]['cost_usd'])
        self.assertNotIn('SECRET-PROMPT', json.dumps(rows))
        self.assertEqual(rows[0]['outcome'], 'Not established from transcript')

    def test_claude_streaming_chunks_are_not_added_as_extra_usage(self):
        path = self.root / 'session.jsonl'
        rows = []
        for output in (2, 5):
            rows.append({'type': 'assistant', 'sessionId': 's', 'cwd': '/example/project',
                'message': {'id': 'provider-1', 'usage': {'input_tokens': 3, 'cache_read_input_tokens': 10,
                    'cache_creation_input_tokens': 4, 'output_tokens': output},
                    'content': [{'type': 'tool_use', 'name': 'Skill', 'input': {'skill': 'adlc5:adlc5'}}]}})
        path.write_text('\n'.join(json.dumps(row) for row in rows))
        result, _ = sessions([('claude', self.root)], [])
        self.assertEqual(result[0]['tokens'], 22)

    def test_symlinked_feature_tree_is_not_followed(self):
        outside = self.root / 'outside'
        (outside / '.adlc5/secret').mkdir(parents=True)
        repo = self.root / 'repo'
        repo.mkdir()
        (repo / '.adlc5').symlink_to(outside / '.adlc5')
        result = collect([repo], [])
        self.assertEqual(result['features'], [])
        self.assertTrue(result['warnings'])


if __name__ == '__main__':
    unittest.main()
