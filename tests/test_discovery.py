import tempfile
import unittest
from pathlib import Path

from benchmark_harness.cli import discover


class DiscoveryTests(unittest.TestCase):
    def test_missing_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            row = discover(Path(directory) / "benchmarks", "rust", None)
            self.assertEqual(row["status"], "unavailable")
            self.assertIn("Cargo.toml", row["reason"])

    def test_override_requires_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            row = discover(Path(directory), "cpp", directory)
            self.assertEqual(row["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
