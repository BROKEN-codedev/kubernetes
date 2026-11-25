# Validation on 25 November 2026

| Check | Observed result on macOS |
|---|---|
| Unit, CLI and wheel installation suite | 50 passed, 0 failures or errors |
| Statement coverage | 241/245 (98.37%), 85% gate passed |
| Branch outcomes | 110/116 (94.83%) |
| Combined coverage.py result | 351/361 (97.23%), zero excluded lines |
| Installed module and kubectl scenarios | Healthy 0, degraded 1, critical 2, empty 3 |
| Native integration | kubectl v1.36.1 discovered the venv executable and forwarded arguments outside the checkout |
| Distribution | Standard-library wheel build and fresh pip installation with --no-index passed |

The suite exercises the module launcher in a child process. Its two statements remain unmeasured by the parent coverage process. See [reproduction commands](../RUN_AND_TEST.md). The evidence directory contains the earlier November 12 audit.

The fork runs the repository-level `.github/workflows/namespace-health.yml`. Select the push matching your commit in [Namespace health checks](https://github.com/BROKEN-codedev/kubernetes/actions/workflows/namespace-health.yml). Validation uses local snapshots throughout.
