"""Consumer-owned checks, run outside the writable consumer repository."""
import csv
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, sys.argv.pop(1))
CASE = sys.argv.pop(1)
import app


class Acceptance(unittest.TestCase):
    def test_frozen_requirement(self):
        if CASE == 'tiny-label':
            self.assertEqual(app.label('  iPhone USB '), 'iPhone USB')
        elif CASE == 'tiny-total':
            self.assertEqual(app.total([{'quantity': 2}, {}]), 2)
        elif CASE == 'standard-search':
            self.assertEqual(app.search([{'name': 'Apple'}, {'name': 'pear'}], ' APP '), [{'name': 'Apple'}])
        elif CASE == 'standard-export':
            rows = list(csv.reader(io.StringIO(app.export([{'name': 'pear, ripe', 'quantity': 2}, {'name': 'a"b', 'quantity': 0}]))))
            self.assertEqual(rows, [['name', 'quantity'], ['pear, ripe', '2'], ['a"b', '0']])
        elif CASE == 'risk-path':
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / 'root'
                root.mkdir()
                secret = Path(folder) / 'secret'
                secret.write_text('private')
                (root / 'safe').write_text('ok')
                (root / 'link').symlink_to(secret)
                self.assertEqual(app.read_item(root, 'safe'), 'ok')
                for name in ('../secret', str(secret), 'link'):
                    with self.assertRaises(ValueError, msg=name):
                        app.read_item(root, name)
        elif CASE == 'risk-save':
            from unittest.mock import patch
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'items.json'
                path.write_text('["original"]')
                with self.assertRaises(TypeError):
                    app.save_items(path, [object()])
                self.assertEqual(path.read_text(), '["original"]')
                with patch('os.replace', side_effect=OSError('simulated interrupted replacement')):
                    with self.assertRaises(OSError):
                        app.save_items(path, [{'name': 'new'}])
                self.assertEqual(json.loads(path.read_text()), ['original'])
                app.save_items(path, [{'name': 'new'}])
                self.assertEqual(json.loads(path.read_text()), [{'name': 'new'}])
                self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ['items.json'])
        else:
            self.fail('unknown case')


if __name__ == '__main__':
    unittest.main()
