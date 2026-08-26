import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmark_harness.cli import benchmark_idris2, discover


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

    def test_idris2_missing_compiler_is_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            implementation = root / "implementation"
            implementation.mkdir()
            (implementation / "gafro.ipkg").write_text("package fixture\n")
            args = type("Args", (), {
                "idris2_path": str(implementation),
                "idris2_compiler": "missing-idris2",
                "idris2_backend": "chez",
                "profile": "smoke",
            })()
            with patch("benchmark_harness.cli.shutil.which", return_value=None):
                with self.assertRaisesRegex(SystemExit, "Idris 2 compiler not found"):
                    benchmark_idris2(args, root, {"workloads": []}, 1000)

    def test_idris_adapter_declares_totality_and_provenance(self):
        source = (Path(__file__).resolve().parents[1] / "idris2/src/Main.idr").read_text()
        self.assertIn("%default total", source)
        self.assertIn('"--backend"', source)
        self.assertIn('"--c-compiler"', source)
        self.assertIn('"--c-flags"', source)


if __name__ == "__main__":
    unittest.main()
