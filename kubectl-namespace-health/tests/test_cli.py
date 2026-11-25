import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ns_health.cli import main
from tests.common import snapshot

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(list(args))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_four_scenarios_and_exit_codes(self):
        for name, code, status in [("healthy", 0, "HEALTHY"), ("degraded", 1, "DEGRADED"),
                                    ("critical", 2, "CRITICAL"), ("empty", 3, "UNKNOWN")]:
            with self.subTest(scenario=name):
                got, out, err = self.invoke("--scenario", name, "--json")
                self.assertEqual(got, code)
                self.assertEqual(err, "")
                self.assertEqual(json.loads(out)["status"], status)

    def test_populated_demo_scenarios_include_varied_pods(self):
        for scenario in ("healthy", "degraded", "critical"):
            with self.subTest(scenario=scenario):
                _, out, _ = self.invoke("--scenario", scenario, "--json")
                report = json.loads(out)
                pods = report["pods"]
                self.assertGreaterEqual(len(pods), 10)
                self.assertTrue(all(pod["namespace"] == "demo" for pod in pods))
                self.assertTrue(any(pod["ready"] for pod in pods))
                if scenario != "healthy":
                    self.assertTrue(any(pod["terminating"] for pod in pods))
                    self.assertTrue({"Pending", "Unknown", "Succeeded"} <= {pod["phase"] for pod in pods})
                if scenario == "critical":
                    self.assertIn("Failed", {pod["phase"] for pod in pods})
                    reasons = {reason for pod in pods for reason in pod["waiting_reasons"]}
                    self.assertTrue({"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"} <= reasons)

    def test_default_text_report_includes_required_context(self):
        code, out, err = self.invoke()
        self.assertEqual(code, 0)
        for expected in ["HEALTHY", "simulation", "2026-11-10", "Restart threshold: 5", "demo"]:
            self.assertIn(expected, out)
        self.assertEqual(err, "")

    def test_custom_fixture_options_and_empty_namespace(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "snapshot.json"
            path.write_text(json.dumps(snapshot()), encoding="utf-8")
            code, out, err = self.invoke("--fixture", str(path), "--restart-threshold", "0", "--json")
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["summary"]["total_pods"], 1)
            code, out, err = self.invoke("--fixture", str(path), "-n", "other", "--json")
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(out)["summary"]["total_pods"], 0)

    def test_unknown_namespace_error_is_json(self):
        code, out, err = self.invoke("-n", "absent", "--json")
        self.assertEqual(code, 3)
        self.assertEqual(err, "")
        self.assertIn("unknown namespace", json.loads(out)["error"])

    def test_missing_and_invalid_files_are_not_empty_success(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "input.json"
            for content in [None, "{broken", "null", "\udcff"]:
                if content is not None:
                    path.write_bytes(content.encode("utf-8", errors="surrogatepass"))
                code, out, err = self.invoke("--fixture", str(path), "--json")
                self.assertEqual(code, 3)
                self.assertEqual(json.loads(out)["status"], "UNKNOWN")
                self.assertEqual(err, "")

    def test_text_errors_go_to_stderr(self):
        code, out, err = self.invoke("-n", "absent")
        self.assertEqual(code, 3)
        self.assertEqual(out, "")
        self.assertIn("unknown namespace", err)
        self.assertNotIn("Traceback", err)

    def test_oversized_json_integer_is_a_structured_input_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "large-integer.json"
            path.write_text('[' + '9' * 5000 + ']')
            code, out, err = self.invoke("--fixture", str(path), "--json")
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out)["status"], "UNKNOWN")
        self.assertEqual(err, "")

    def test_invalid_argument_usage_exits_two(self):
        for args in [("--scenario", "nope"), ("--recent-minutes", "0"),
                     ("--restart-threshold", "-1"), ("--unknown",),
                     ("--scenario", "healthy", "--fixture", "input.json")]:
            with self.subTest(args=args):
                code, out, err = self.invoke(*args)
                self.assertEqual(code, 2)
                self.assertIn("usage:", err)

    def test_nonstandard_json_constants_are_input_errors(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "nonstandard.json"
            for constant in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(constant=constant):
                    content = json.dumps(snapshot())[:-1] + ', "extra": ' + constant + '}'
                    path.write_text(content, encoding="utf-8")
                    code, out, err = self.invoke("--fixture", str(path), "--json")
                    self.assertEqual(code, 3)
                    self.assertEqual(json.loads(out)["status"], "UNKNOWN")
                    self.assertIn("invalid JSON", json.loads(out)["error"])
                    self.assertEqual(err, "")

    def test_nonstandard_constant_names_inside_strings_are_valid(self):
        data = snapshot()
        data["extra"] = "NaN Infinity -Infinity"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "strings.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            code, out, err = self.invoke("--fixture", str(path), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "HEALTHY")
        self.assertEqual(err, "")

    def test_oversized_fixture_is_an_input_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "oversized.json"
            with path.open("wb") as stream:
                stream.truncate(16 * 1024 * 1024 + 1)
            code, out, err = self.invoke("--fixture", str(path), "--json")
        self.assertEqual(code, 3)
        self.assertIn("16 MiB", json.loads(out)["error"])
        self.assertEqual(err, "")

    def test_directory_and_deeply_nested_json_are_input_errors(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "nested.json"
            path.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
            for target in (Path(d), path):
                with self.subTest(target=target):
                    code, out, err = self.invoke("--fixture", str(target), "--json")
                    self.assertEqual(code, 3)
                    self.assertEqual(json.loads(out)["status"], "UNKNOWN")
                    self.assertIn("error", json.loads(out))
                    self.assertEqual(err, "")

    def test_text_and_json_agree_on_health_counters_and_reasons(self):
        for scenario in ("healthy", "degraded", "critical", "empty"):
            with self.subTest(scenario=scenario):
                json_code, json_out, json_err = self.invoke("--scenario", scenario, "--json")
                text_code, text_out, text_err = self.invoke("--scenario", scenario)
                report = json.loads(json_out)
                self.assertEqual(text_code, json_code)
                self.assertEqual(text_err, "")
                self.assertEqual(json_err, "")
                self.assertIn(report["status"], text_out)
                self.assertIn(f"{report['summary']['ready_pods']}/{report['summary']['evaluated_pods']} evaluated ready", text_out)
                self.assertIn(f"Cumulative restarts: {report['summary']['total_restarts']}", text_out)
                self.assertIn(f"Recent Warning records: {report['summary']['recent_warning_records']}", text_out)
                for reason in report["reasons"]:
                    self.assertIn(reason, text_out)

    def test_now_override_is_validated(self):
        code, out, err = self.invoke("--now", "no-time", "--json")
        self.assertEqual(code, 3)
        self.assertIn("timestamp", json.loads(out)["error"])
        code, out, err = self.invoke("--now", "2026-11-11T00:00:00+05:30", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["reference_time"], "2026-11-10T18:30:00+00:00")

    def test_help_and_version(self):
        for args, expected in [(('--help',), 'namespace'), (('--version',), '1.0.0')]:
            code, out, err = self.invoke(*args)
            self.assertEqual(code, 0)
            self.assertIn(expected, out)

    def test_module_entry_point_uses_real_process_exit(self):
        p = subprocess.run([sys.executable, "-m", "ns_health", "--scenario", "critical", "--json"],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["status"], "CRITICAL")

    def test_launcher_works_outside_repository(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, str(ROOT / "bin/kubectl-ns_health"), "--json"],
                               cwd=d, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "HEALTHY")
