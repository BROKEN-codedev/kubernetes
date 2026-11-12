import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

from scripts.build_wheel import build_wheel


class PackagingTests(unittest.TestCase):
    def test_wheel_install_runs_offline_outside_source_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            wheel = build_wheel(root / "wheels")
            self.assertTrue(wheel.is_file(), "builder must produce an installable wheel")
            target = root / "env"
            venv.create(target, with_pip=True)
            bindir = target / ("Scripts" if sys.platform == "win32" else "bin")
            python = bindir / ("python.exe" if sys.platform == "win32" else "python")
            install = subprocess.run([str(python), "-m", "pip", "install", "--no-index", str(wheel)],
                                     cwd=root, capture_output=True, text=True)
            self.assertEqual(install.returncode, 0, install.stderr)
            for scenario, expected in [("healthy", 0), ("degraded", 1), ("critical", 2), ("empty", 3)]:
                result = subprocess.run([str(python), "-m", "ns_health", "--scenario", scenario, "--json"],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(json.loads(result.stdout)["exit_code"], expected)
            executable = bindir / ("kubectl-ns_health.exe" if sys.platform == "win32" else "kubectl-ns_health")
            result = subprocess.run([str(executable), "--json"], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["source"], "simulation")
