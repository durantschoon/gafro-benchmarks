"""Tests for the standalone shootout runner, runner/run_all.py."""

import contextlib
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "runner" / "run_all.py"


def load_runner():
    """Import runner/run_all.py by path; it is a script, not a package."""
    spec = importlib.util.spec_from_file_location("gafro_run_all", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def v1_row(family, workload, samples, operations=10, status="supported"):
    row = {
        "schema_version": "gafro-benchmark-result/v1",
        "implementation": {"family": family},
        "workload_id": workload,
        "status": status,
        "reason": "",
    }
    if status == "supported":
        row.update(sample_durations_ns=list(samples), operations_per_sample=operations)
    return row


SHARED = "motor_composition_gp/f64/scalar"
JULIA_ONLY = "spatial_inertia_action/f64/wrench_checksum"
CPP_ONLY = "point_transform/f64/scalar"


def markdown_table(markdown):
    lines = [line for line in markdown.splitlines() if line.startswith("|")]
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = {}
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows[cells[0].strip("`")] = dict(zip(header, cells))
    return header, rows, lines


class ShootoutRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def fixture_members(self):
        return {
            # Flat legacy shape (PORTING_AND_STANDARDS.md section 2).
            "cpp": {"results": [
                {"benchmark": SHARED, "time_per_op_ns": 10.0, "ops_per_sec": 1e8},
                {"benchmark": CPP_ONLY, "time_per_op_ns": 4.0, "ops_per_sec": 2.5e8},
            ]},
            # v1 shape: median(200, 250, 300) / 10 = 25 ns/op.
            "rust": {"results": [v1_row("rust", SHARED, (200, 250, 300))]},
            # v1 shape: median(400, 500, 600) / 10 = 50 ns/op; plus a workload
            # only julia implements.
            "julia": {"results": [
                v1_row("julia", SHARED, (400, 500, 600)),
                v1_row("julia", JULIA_ONLY, (70, 80, 90)),
            ]},
        }

    def test_render_table_has_julia_column_ratio_and_union(self):
        terminal, markdown = self.runner.render_table(self.fixture_members())
        header, rows, lines = markdown_table(markdown)

        self.assertIn("Julia Latency", header)
        self.assertIn("Relative Speed (C++/Julia)", header)
        self.assertLess(header.index("Rust Latency"), header.index("Julia Latency"))
        self.assertLess(header.index("Relative Speed (C++/Rust)"), header.index("Relative Speed (C++/Julia)"))
        width = len(lines[0].split("|"))
        for line in lines[1:]:
            self.assertEqual(len(line.split("|")), width, line)

        shared = rows[SHARED]
        self.assertEqual(shared["C++26 Latency"], "10.00")
        self.assertEqual(shared["Rust Latency"], "25.00")
        self.assertEqual(shared["Julia Latency"], "50.00")
        self.assertEqual(shared["Relative Speed (C++/Rust)"], "**2.50x faster**")
        self.assertEqual(shared["Relative Speed (C++/Julia)"], "**5.00x faster**")
        self.assertEqual(shared["F* Latency (in-VM)"], "absent")

        # Union semantics: the julia-only workload is present, and every
        # ratio with a missing side is n/a.
        julia_only = rows[JULIA_ONLY]
        self.assertEqual(julia_only["Julia Latency"], "8.00")
        self.assertEqual(julia_only["C++26 Latency"], "absent")
        self.assertEqual(julia_only["Relative Speed (C++/Julia)"], "**n/a**")
        self.assertEqual(julia_only["Relative Speed (C++/Rust)"], "**n/a**")
        cpp_only = rows[CPP_ONLY]
        self.assertEqual(cpp_only["Julia Latency"], "absent")
        self.assertEqual(cpp_only["Relative Speed (C++/Julia)"], "**n/a**")

        # Row order: C++'s keys first, then keys new to later members.
        self.assertEqual(list(rows), [SHARED, CPP_ONLY, JULIA_ONLY])

        self.assertIn("Ratio (C++/Julia)", terminal)
        self.assertIn("Julia (ns)", terminal)
        self.assertIn(JULIA_ONLY, terminal)

    def test_render_table_unsupported_julia_row_shows_status(self):
        members = self.fixture_members()
        members["julia"]["results"][0] = v1_row("julia", SHARED, (), status="unsupported")
        _, markdown = self.runner.render_table(members)
        _, rows, _ = markdown_table(markdown)
        self.assertEqual(rows[SHARED]["Julia Latency"], "unsupported")
        self.assertEqual(rows[SHARED]["Relative Speed (C++/Julia)"], "**n/a**")

    def test_render_table_is_pure(self):
        members = self.fixture_members()
        with patch("subprocess.run") as run, patch("builtins.open") as opened:
            first = self.runner.render_table(members)
            second = self.runner.render_table(members)
        run.assert_not_called()
        opened.assert_not_called()
        self.assertEqual(first, second)


class ShootoutPartialRunGuardTests(unittest.TestCase):
    def assert_refused_before_running(self, argv):
        runner = load_runner()
        names = ("build_cpp", "build_rust", "build_fstar", "build_julia",
                 "run_cpp", "run_rust", "run_fstar", "run_julia")
        with contextlib.ExitStack() as stack:
            # A relative --output-dir is resolved against the working directory.
            stack.enter_context(contextlib.chdir(ROOT))
            mocks = [stack.enter_context(patch.object(runner, name)) for name in names]
            stack.enter_context(patch.object(runner.subprocess, "run"))
            with self.assertRaises(SystemExit) as raised:
                runner.main(argv)
        for mock in mocks:
            mock.assert_not_called()
        self.assertNotIn(raised.exception.code, (0, None))
        self.assertIn("--output-dir", str(raised.exception.code))

        # Same refusal from the real script: non-zero exit, one-line reason
        # on stderr, nothing on stdout.
        completed = subprocess.run([sys.executable, str(RUNNER), *argv],
                                   capture_output=True, text=True, cwd=str(ROOT))
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertIn("--output-dir", completed.stderr)
        self.assertEqual(len(completed.stderr.strip().splitlines()), 1)

    def test_partial_members_without_output_dir_is_refused(self):
        self.assert_refused_before_running(["--members", "julia"])

    def test_partial_members_into_results_is_refused(self):
        self.assert_refused_before_running(["--members", "julia", "--output-dir", "results"])
        self.assert_refused_before_running(["--members", "julia", "--output-dir", str(ROOT / "results")])



FSTAR_RUNNER = ROOT / "fstar" / "run_fstar.py"


def load_fstar_runner():
    """Import fstar/run_fstar.py by path; it is a script, not a package."""
    spec = importlib.util.spec_from_file_location("gafro_run_fstar", FSTAR_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnvelopeLayoutDiscoveryTests(unittest.TestCase):
    """The standalone runners find egafro-<family>/gafro-<family> checkouts."""

    def test_julia_and_fstar_discover_envelope_layout(self):
        import tempfile
        run_all = load_runner()
        run_fstar = load_fstar_runner()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "egafro-benchmarks" / "gafro-benchmarks"
            root.mkdir(parents=True)
            julia = base / "egafro-julia" / "gafro-julia"
            julia.mkdir(parents=True)
            (julia / run_all.JULIA_MARKER).write_text("fixture\n")
            fstar = base / "egafro-fstar" / "gafro-fstar"
            (fstar / run_fstar.MARKER).parent.mkdir(parents=True)
            (fstar / run_fstar.MARKER).write_text("fixture\n")
            with patch.object(run_all, "ROOT_DIR", root):
                self.assertEqual(run_all.discover_julia(), julia.resolve())
            with patch.object(run_fstar, "ROOT_DIR", root), \
                    patch.dict("os.environ", {}, clear=False) as environment:
                environment.pop("GAFRO_FSTAR_PATH", None)
                found = run_fstar.discover(None)
            self.assertEqual(found, {"status": "available", "path": str(fstar.resolve())})


if __name__ == "__main__":
    unittest.main()
