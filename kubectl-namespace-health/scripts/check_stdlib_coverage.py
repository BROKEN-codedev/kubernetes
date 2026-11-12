"""Run tests and report executed-line coverage without third-party packages.

This is a stdlib trace measurement, not coverage.py statement/branch coverage.
The CI workflow separately enforces coverage.py's 85% statement target.
"""
import json
from pathlib import Path
import sys
import trace
from types import CodeType
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def executable_lines(code):
    lines = {line for _, _, line in code.co_lines() if line is not None and line > 0}
    for item in code.co_consts:
        if isinstance(item, CodeType):
            lines.update(executable_lines(item))
    return lines


def run_tests():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    return unittest.TextTestRunner(verbosity=1).run(suite)


if __name__ == "__main__":
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.base_prefix])
    result = tracer.runfunc(run_tests)
    counts = tracer.results().counts
    files = []
    for source in sorted((ROOT / "ns_health").glob("*.py")):
        possible = executable_lines(compile(source.read_text(), str(source), "exec"))
        hit = {line for (filename, line), count in counts.items() if filename == str(source) and count > 0}
        files.append({"file": source.relative_to(ROOT).as_posix(), "executable_lines": len(possible),
                      "executed_lines": len(possible & hit), "missing": sorted(possible - hit)})
    total = sum(f["executable_lines"] for f in files)
    covered = sum(f["executed_lines"] for f in files)
    report = {"measurement": "stdlib trace executed-line coverage; not coverage.py", "files": files,
              "covered": covered, "total": total, "percent": round(100 * covered / total, 2),
              "tests_run": result.testsRun, "successful": result.wasSuccessful()}
    evidence = ROOT / "docs/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "stdlib_coverage.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
