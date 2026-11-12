# Final local validation — 12 November 2026 (India time)

The existing implementation was audited and strengthened on 12 November. The checks below were actually executed with Python 3.14.6 on macOS; the environment is recorded in `evidence/environment.json`. This record supersedes the earlier 11 November validation summary.

| Requirement / check | Command or method | Observed result | Evidence |
|---|---|---|---|
| Unit, CLI and fresh installation tests | `.venv/bin/python -m unittest discover -s tests -v` | 47 tests passed, exit 0 | `evidence/unittest.txt` |
| Reject invalid nonstandard JSON constants | Real files containing NaN, Infinity, -Infinity | Regression failed before fix (3 subtest failures); now passes in full suite | `evidence/json_constants_before_fix.txt`, `evidence/unittest.txt` |
| Healthy fixture | Installed module outside source directory | HEALTHY, exit 0; 2/2 ready, 1 restart, 0 recent warnings | `evidence/healthy.txt`, `evidence/healthy.json` |
| Degraded fixture | Installed module outside source directory | DEGRADED, exit 1; 1/2 ready, 8 restarts, 1 recent warning | `evidence/degraded.txt`, `evidence/degraded.json` |
| Critical fixture | Installed module outside source directory | CRITICAL, exit 2; 0/2 ready, 14 restarts, 1 recent warning | `evidence/critical.txt`, `evidence/critical.json` |
| Empty fixture | Installed module outside source directory | UNKNOWN, exit 3; zero pods | `evidence/empty.txt`, `evidence/empty.json` |
| JSON/text agreement | Parse each scenario JSON; compare expected codes/counters and reasons against text | All four scenarios agree; stdout/stderr separation passes | `evidence/scenario_results.json`, CLI tests |
| Offline wheel build | `.venv/bin/python scripts/build_wheel.py` | Wheel built successfully, exit 0 | `evidence/wheel_build.txt` |
| Wheel installation | Fresh-venv packaging test plus local pip --no-index install | Passed; installed package runs from another working directory | `evidence/unittest.txt`, `evidence/offline_install.txt` |
| Installed console command | `.venv/bin/kubectl-ns_health --json` from temporary directory | HEALTHY, exit 0 | `evidence/installed_cli.txt` |
| Real kubectl discovery | `kubectl plugin list --name-only` with local venv PATH | Plugin discovered, exit 0 | `evidence/plugin_discovery.txt` |
| Real kubectl invocation | `kubectl ns-health --scenario healthy --json` outside source directory | HEALTHY, exit 0; fixture mode only | `evidence/kubectl_healthy.txt` |
| Stdlib executed-line coverage | `python3 scripts/check_stdlib_coverage.py` | 247/254 executable lines, 97.24%; 47 tests pass | `evidence/stdlib_coverage.json` |
| Formal coverage.py statement target >=85% | Attempted local dependency installation; README provides run/report commands | NOT RUN: coverage.py absent, PyPI name resolution failed; subsequent download attempt also failed | `evidence/coverage_install.txt`, `RUN_AND_TEST.md` |
| CI configuration | Workflow inspected | Python 3.11, 3.12 and 3.14; 10-minute bound; formal coverage gate configured | `.github/workflows/ci.yml` |
| Remote GitHub Actions | Requires publishing source to a Git repository | NOT RUN | No remote result claimed |
| Real demo recording / mentor acceptance | User records and submits demonstration | NOT PERFORMED | `DEMO.md` provides a script only |

## Coverage limits

The 97.24% result is an actual standard-library trace executed-line measurement. It is neither coverage.py statement coverage nor branch coverage and does not establish the formal 85% statement acceptance target. Module launchers run in subprocesses and are not traced into this aggregate; no production module is excluded to hide that limit. The commands in `RUN_AND_TEST.md` and CI enforce the formal measurement when coverage.py is available. Optional branch commands are separately documented.

## Review findings and fixes

Python's JSON decoder permits NaN/Infinity by default. In an unused input field these constants previously passed validation and produced HEALTHY despite the fixture not being valid standard JSON. A real-file regression reproduced all three forms first. The parser now rejects nonstandard constants through its parse_constant hook and returns the existing structured UNKNOWN input error, exit 3. Ordinary quoted strings containing the same names remain valid.

Added focused tests for timestamp/status precedence, Failed alongside Ready pods, duplicate identities, malformed conditions/resource kinds/messages, impossible time windows, oversized files, directory paths, deep JSON, and text/JSON agreement. The earlier deferred precedence assertions are now covered. No unrelated health-policy or cluster integration feature was added.

The first ad hoc evidence capture incorrectly expected 13 cumulative critical restarts; direct inspection confirmed 12 + 2 = 14, excluding the completed pod. The verification expectation was corrected and all four scenarios passed. Production scoring did not change.

## Remaining acceptance and external steps

The simulation is runnable, the expanded local suite passes and offline packaging/kubectl execution work. Formal coverage measurement is still blocked by the unavailable development dependency. The source artifact is not a Git repository and has not been pushed. Remote CI, a real demo video and mentor acceptance remain pending. Historical logbook files were not changed by this final audit.
