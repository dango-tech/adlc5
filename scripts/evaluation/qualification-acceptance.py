"""Independent behavioral oracle for the six additional qualification cases."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, sys.argv.pop(1))
CASE = sys.argv.pop(1)
import scenarios


class Acceptance(unittest.TestCase):
    def test_frozen_behavior(self):
        if CASE == 'discover-display':
            self.assertEqual(scenarios.display_name('  iPhone  USB '), 'iPhone  USB')
            self.assertEqual(scenarios.display_name('   '), '')
        elif CASE == 'conflicting-order':
            rows = [{'name': 'A', 'created': 1}, {'name': 'Z', 'created': 3}, {'name': 'B', 'created': 3}]
            before = list(rows)
            result = scenarios.ordered(rows)
            self.assertEqual(result, [rows[1], rows[2], rows[0]])
            self.assertEqual(rows, before)
            self.assertIs(result[0], rows[1])
        elif CASE in ('tenant-export', 'changed-export'):
            records = [{'tenant': 'one', 'name': 'mine'}, {'tenant': 'two', 'name': 'private'}]
            before = [dict(row) for row in records]
            self.assertEqual(scenarios.export_records(records, 'one', 'admin'), [records[0]])
            self.assertEqual(scenarios.export_records(records, 'absent', 'admin'), [])
            for role in ('member', 'guest', '', None):
                with self.assertRaises(PermissionError):
                    scenarios.export_records(records, 'one', role)
            self.assertEqual(records, before)
        elif CASE == 'recover-migration':
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'data.json'
                original = '[{"name":"existing","quantity":2}]'
                path.write_text(original)
                with patch('os.replace', side_effect=OSError('interrupted')):
                    with self.assertRaises(OSError):
                        scenarios.migrate(path)
                self.assertEqual(path.read_text(), original)
                self.assertEqual(list(path.parent.iterdir()), [path])
                scenarios.migrate(path)
                self.assertEqual(json.loads(path.read_text()), {'schema_version': 2, 'items': json.loads(original)})
                first = path.read_bytes()
                scenarios.migrate(path)
                self.assertEqual(path.read_bytes(), first)
        elif CASE == 'retry-delivery':
            delivered = set()
            sender = Mock(side_effect=[TimeoutError(), TimeoutError(), 'ok'])
            self.assertEqual(scenarios.deliver(sender, {'name': 'x'}, 'key', delivered), 'ok')
            self.assertEqual(sender.call_count, 3)
            self.assertIsNone(scenarios.deliver(sender, {}, 'key', delivered))
            self.assertEqual(sender.call_count, 3)
            sender = Mock(side_effect=TimeoutError())
            with self.assertRaises(TimeoutError):
                scenarios.deliver(sender, {}, 'other', delivered)
            self.assertEqual(sender.call_count, 3)
            self.assertNotIn('other', delivered)
            sender = Mock(side_effect=ValueError('permanent'))
            with self.assertRaises(ValueError):
                scenarios.deliver(sender, {}, 'permanent', delivered)
            self.assertEqual(sender.call_count, 1)
        else:
            self.fail('unknown qualification case')


if __name__ == '__main__':
    unittest.main()
