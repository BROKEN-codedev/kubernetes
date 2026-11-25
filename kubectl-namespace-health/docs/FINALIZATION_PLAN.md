# Finalization plan — 12 November 2026

Historical November 2026 record. See [current validation](VALIDATION.md) for subsequent results.

Goal: finish the existing simulation against docs/PRD.md, README policy and the shared behavior contract. Keep the standard-library runtime, existing CLI and namespace health rules.

- [x] Strengthen health tests for unknown-warning/critical precedence, failed pods alongside ready pods, invalid resource identities and date-range overflow. Tests use literal status/counter expectations.
- [x] Strengthen CLI checks for the 16 MiB limit, unreadable paths, deeply nested JSON, text/JSON agreement and malformed options. Change runtime code only for a reproduced contract failure.
- [x] Run the full suite and standard-library trace measurement. Attempt formal coverage.py measurement and preserve the actual outcome, including dependency/network blockers.
- [x] Rebuild the wheel, install it offline in a fresh venv, run all scenarios outside the project, and check real kubectl discovery/invocation without cluster access.
- [x] Bound CI execution, include the advertised minimum Python version, refresh validation/demo/setup instructions and package a clean ZIP containing source, tests, wheel and actual evidence.

No Git repository is present in this artifact directory. Work here does not push or publish source or change the synced reference files. Remote CI, a recorded demo and mentor acceptance require separate observed evidence.
