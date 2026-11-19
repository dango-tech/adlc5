"""Run from an operator environment against a checked-out worker revision."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class BrownfieldOracle(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.stock = Path(directory.name) / "stock.json"
        self.rows = [
            {"sku": "Z9", "name": "Café", "quantity": 2, "legacy": {"x": [1, None]}},
            {"sku": "a1", "name": "é", "quantity": 5, "legacy": False},
            {"sku": "A1", "name": "Other", "quantity": 0},
        ]
        self.original = json.dumps(self.rows, ensure_ascii=False, indent=4).encode("utf-8")
        self.stock.write_bytes(self.original)

    def test_preview_matches_commit_without_writing(self):
        requests = {"a1": 4, "Z9": 2}
        self.assertEqual(app.reserve_stock(self.stock, requests, preview=True), requests)
        self.assertEqual(self.stock.read_bytes(), self.original)
        self.assertEqual(app.reserve_stock(self.stock, requests), requests)

        self.rows[0]["quantity"] = 0
        self.rows[1]["quantity"] = 1
        self.assertEqual(json.loads(self.stock.read_text(encoding="utf-8")), self.rows)
        self.assertEqual(reporting.read_stock(self.stock), [("Z9", 0), ("a1", 1), ("A1", 0)])

    def test_rejections_leave_file_unchanged(self):
        rejected_batches = [
            {"a1": 1, "Z9": 3},
            {"a1": 1, "A1": 1},
            {"a1": 1, "missing": 1},
            *({"a1": 1, "Z9": value} for value in (0, -1, True, 1.5, "1")),
        ]
        for preview in (True, False):
            for requests in rejected_batches:
                with self.subTest(preview=preview, requests=requests):
                    with self.assertRaises(ValueError):
                        app.reserve_stock(self.stock, requests, preview=preview)
                    self.assertEqual(self.stock.read_bytes(), self.original)

    def test_failed_atomic_publication_preserves_previous_file(self):
        with (
            patch("os.replace", side_effect=OSError("injected publication failure")) as replace,
            patch("os.rename", side_effect=OSError("injected publication failure")) as rename,
        ):
            with self.assertRaises(OSError):
                app.reserve_stock(self.stock, {"a1": 4})
        self.assertTrue(replace.called or rename.called, "injection did not reach publication")
        self.assertEqual(self.stock.read_bytes(), self.original)
        self.assertEqual(reporting.read_stock(self.stock), [("Z9", 2), ("a1", 5), ("A1", 0)])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: oracle.py /path/to/consumer-checkout")
    sys.path.insert(0, str(Path(sys.argv.pop()).resolve()))
    app = importlib.import_module("app")
    reporting = importlib.import_module("reporting")
    unittest.main()
