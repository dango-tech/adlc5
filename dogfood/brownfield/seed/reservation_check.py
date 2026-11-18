"""Public PR acceptance check. It is expected to start red."""
from pathlib import Path
import shutil
import tempfile
import unittest

import app
from reporting import read_stock


class ReservationCheck(unittest.TestCase):
    def test_preview_and_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            stock = Path(directory) / "stock.json"
            shutil.copyfile(Path(__file__).parent / "fixtures/legacy-stock.json", stock)
            original = stock.read_bytes()
            requests = {"A-01": 3, "B-02": 2}
            self.assertEqual(app.reserve_stock(stock, requests, preview=True), requests)
            self.assertEqual(stock.read_bytes(), original)
            self.assertEqual(app.reserve_stock(stock, requests), requests)
            self.assertEqual(read_stock(stock), [("B-02", 2), ("A-01", 4), ("Z-09", 0)])


if __name__ == "__main__":
    unittest.main()
