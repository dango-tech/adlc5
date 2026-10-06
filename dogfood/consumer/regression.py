import unittest
import app


class Regression(unittest.TestCase):
    def test_existing_behaviour(self):
        self.assertEqual(app.label('  Apple '), 'Apple')
        self.assertEqual(app.total([{'quantity': 2}, {'quantity': 3}]), 5)
        self.assertEqual(app.search([{'name': 'apple'}], 'apple'), [{'name': 'apple'}])
        self.assertIsInstance(app.export([]), str)


if __name__ == '__main__':
    unittest.main()
