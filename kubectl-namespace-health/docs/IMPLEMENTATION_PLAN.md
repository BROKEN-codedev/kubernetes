# Namespace Health Plugin Implementation Plan

**Goal:** Deliver the original Python simulation plugin with reproducible examples, tests and evidence.
**Architecture:** Validate Kubernetes-shaped JSON, select one namespace, compute a pure health report, then render text/JSON in a thin CLI. Bundle four fixed-time scenarios. No cluster access.
**Tech stack:** Python 3.11+, standard-library runtime, unittest; coverage.py when available.
**Spec:** Shared behavior contract in the companion OJT Codex prompt pack.

## Constraints and review focus

- Preserve the original 90-page logbook and only fill its blank areas.
- Record current coding work on 11 November 2026; do not backdate it.
- Preserve namespace isolation, timezone-aware boundary comparisons, completed-pod handling, truthful empty/error status and cwd-independent examples.
- Use a standalone artifact directory, not the Kubernetes fork or project-mirror git metadata.

## Task 1 - Analysis and fixtures

Files: `ns_health/health.py`, `ns_health/data/*.json`, `tests/test_health.py`.
Interface: `analyze(data, namespace='demo', recent_minutes=60, restart_threshold=5, now=None) -> dict` raises `InputError` for invalid data.

- [x] Write real tests with literal expected counts for fixtures, readiness, restarts, namespaces and event boundaries.
- [x] Run the tests against a deliberate unimplemented stub; require assertion failures before implementation.
- [x] Implement parsing, validation and deterministic analysis.
- [x] Run the entire analysis suite.

## Task 2 - CLI and execution

Files: `ns_health/cli.py`, `ns_health/__main__.py`, `bin/kubectl-ns_health`, `pyproject.toml`, `tests/test_cli.py`.
Interface: `main(argv=None) -> int`; command output and exit codes follow the shared contract.

- [x] Write CLI tests for expected statuses, JSON, flags, missing inputs and installed/cwd-independent execution.
- [x] Run against the unimplemented CLI and observe failures.
- [x] Implement the CLI, package resources, launcher and local installation path.
- [x] Run all tests and all four real scenario commands.

## Task 3 - Evidence and documentation

Files: README, license, contribution guide, CI workflow, docs/PRD, DESIGN, TEST_CASES, VALIDATION, DEMO, evidence/.

- [x] Execute a fresh-environment installation and examples; measure actual coverage if tooling is available.
- [x] Save actual outputs and label unavailable remote checks as not run.
- [x] Review the whole project with a fresh reviewer; fix material findings with a failing test first.
- [x] Package source, tests and evidence into a ZIP.

## Task 4 - Logbook

- [x] Fill confirmed personal details, all 37 dates, Open Source Track, Student and the user-reported estimated 22:00-23:30 window in the untouched original PDF.
- [x] Use dated research evidence and clearly marked planning drafts for dates without records.
- [x] Put current implementation/test results in a separate 11 November completion record.
- [x] Verify all 90 original pages remain, blank-area overlays fit, and original page content is preserved.

## Execution ledger

Ruling: deliver a standalone artifact directory rather than changing the mirror's git state; the user requested a runnable project, not a branch or upstream change.
Ruling: historical date allocation remains unverified; actual current coding evidence belongs in the dated supplement.

Task 1 complete: 22 analysis tests observed failing against the stub, then passing.
Task 2 complete: CLI and packaging tests observed failing before implementation, then the full suite passed.
Task 3 implementation complete: local evidence captured; external checks are explicitly pending in VALIDATION.md.
Final review: large-JSON-integer error handling fixed with a failing real-file regression; full suite 35/35.
Initially deferred: explicit unknown-timestamp status-precedence assertions; resolved in the 12 November final audit.
Ruling: unusable warning recency yields UNKNOWN unless known CRITICAL evidence wins, avoiding false healthy output.

## Final audit — 12 November 2026

- [x] Reproduced and fixed nonstandard JSON constants being accepted as healthy input.
- [x] Expanded the suite from 35 to 47 tests, including the previously deferred precedence checks.
- [x] Rebuilt the wheel, verified offline installation and ran all scenarios from outside the project.
- [x] Rechecked real kubectl plugin discovery and invocation with fixture data.
- [x] Refreshed real logs, environment metadata, run instructions and validation report.
- [x] Added the Python 3.11 CI target and a ten-minute job timeout.
- [ ] Formal coverage.py measurement: dependency download blocked; see `VALIDATION.md`.
- [ ] External publication, remote CI, real demo recording and mentor approval.
