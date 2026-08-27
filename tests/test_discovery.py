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
                    benchmark_idris2(args, root, {"workloads": []}, 1000, root / "run")

    def test_idris_adapter_declares_totality_and_provenance(self):
        source = (Path(__file__).resolve().parents[1] / "idris2/src/Main.idr").read_text()
        self.assertIn("%default total", source)
        self.assertIn('"--backend"', source)
        self.assertIn('"--c-compiler"', source)
        self.assertIn('"--c-flags"', source)

    def test_rust_adapter_reports_batch_capabilities_and_provenance(self):
        source = (Path(__file__).resolve().parents[1] / "rust/src/main.rs").read_text()
        self.assertIn("BatchMotorSoA", source)
        self.assertIn("BatchPointSoA", source)
        self.assertIn('"--rustflags"', source)
        self.assertIn("codegen-units: 1", source)
        self.assertIn("lto: fat", source)

    def test_robotics_adapters_declare_matching_capabilities(self):
        root = Path(__file__).resolve().parents[1]
        cpp = (root / "cpp/bench_cga.cpp").read_text()
        rust = (root / "rust/src/main.rs").read_text()
        idris = (root / "idris2/src/Main.idr").read_text()
        fk = "robotics_forward_kinematics_2r/f64/motor_checksum"
        jacobian = "robotics_geometric_jacobian_2r/f64/base_checksum"
        self.assertIn(fk, cpp)
        self.assertIn(jacobian, cpp)
        self.assertIn(fk, rust)
        self.assertIn("fails the canonical base-frame oracle", rust)
        self.assertIn(fk, idris)
        self.assertIn(jacobian, idris)
        self.assertIn("no canonical robotics adapter validated", idris)


if __name__ == "__main__":
    unittest.main()
