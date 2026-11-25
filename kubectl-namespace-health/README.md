# kubectl Namespace Health Plugin (Simulated)

An OJT project by **Ayaan Jindal**, B.Tech in Applied AI, Semester 1, Polaris School of Technology. Mentor: **Abhishek Jagtap**.

Engineers often inspect separate pod and event outputs to assess a namespace. This Python CLI combines Pod Ready conditions, cumulative container restarts and recent Warning event records into one explainable report.

**This is a working simulation, not a connection to a live Kubernetes cluster.** It reads bundled or custom Kubernetes-shaped JSON. It does not repair Kubernetes, change a cluster or represent an upstream Kubernetes contribution. The initial implementation was prepared on **11 November 2026**. AI assistance was used; the student should review the code and demonstrate understanding.

See [RUN_AND_TEST.md](RUN_AND_TEST.md) for a copy-and-paste setup and testing guide, and [docs/CHANGES.md](docs/CHANGES.md) for the final audit changes.

## Run immediately

Requires Python **3.11 or newer**. No third-party runtime dependency, account or cluster is needed.

```bash
cd kubectl-namespace-health
python3 -m ns_health --scenario healthy
python3 -m ns_health --scenario degraded --json
python3 -m ns_health --scenario critical
python3 -m ns_health --scenario empty
```

Nonzero exit codes for degraded, critical and empty are intentional health results. Do not join all demo commands with `&&`, which would stop after the first nonzero result.

## Install offline into a local virtual environment

The project includes an installable wheel under `dist/`. It can also be built using the standard library:

```bash
python3 scripts/build_wheel.py
python3 -m venv .venv
.venv/bin/python -m pip install --no-index dist/kubectl_namespace_health-1.0.0-py3-none-any.whl
.venv/bin/kubectl-ns_health --scenario healthy
```

On Windows use `.venv\Scripts\python.exe` and the corresponding Scripts directory. The offline wheel builder is specific to this pure-Python project. A conventional setuptools build is configured in `pyproject.toml`; `pip install -e .` may download build dependencies.

## Use through kubectl

If kubectl is already installed, add the local venv's bin directory to your current shell's PATH:

```bash
export PATH="$PWD/.venv/bin:$PATH"
kubectl plugin list
kubectl ns-health --scenario healthy -n demo
```

The console script is named `kubectl-ns_health`: the underscore allows `ns-health` as one kubectl command. Source-checkout alternative: `python3 /absolute/path/to/bin/kubectl-ns_health --json`, which also works outside the source directory. Do not move the source launcher away from its parent project; use the installed console script for a portable installation.

## CLI reference

| Flag | Behavior |
|---|---|
| `-n`, `--namespace` | Namespace name; default `demo` |
| `--scenario` | `healthy`, `degraded`, `critical`, `empty`; default healthy |
| `--fixture PATH` | Custom JSON snapshot; exclusive with `--scenario` |
| `--json` | One machine-readable report on stdout |
| `--recent-minutes` | Positive integer; default 60; closed interval ending at reference time |
| `--restart-threshold` | Nonnegative per-pod cumulative total; default 5 |
| `--now` | ISO 8601 timestamp with timezone; overrides fixture reference time |
| `--help`, `--version` | Usage or version |

Examples:

```bash
python3 -m ns_health --fixture ns_health/data/degraded.json -n demo --json
python3 -m ns_health --scenario healthy --restart-threshold 1
python3 -m ns_health --scenario degraded --now 2026-11-11T00:00:00+05:30
```

Every report states `source: simulation` and the actual effective reference time. Bundled examples use **10 November 2026 12:00 UTC** as a fixed simulation clock; it is fixture data, not a claimed live observation or implementation date.

## Health policy

These thresholds are application choices, not Kubernetes-wide standards. Evaluation precedence is critical, then unknown, then degraded, then healthy.

| Status | Exit | Meaning |
|---|---:|---|
| HEALTHY | 0 | Evaluated pods ready, no configured indicator triggered |
| DEGRADED | 1 | A pod unready, a pod's restart sum >= threshold, or a recent Warning record |
| CRITICAL | 2 | Failed pod, CrashLoopBackOff/ImagePullBackOff/ErrImagePull, or evaluated pods with zero ready |
| UNKNOWN | 3 | Empty/completed-only namespace, unusable Warning timestamps, or input failure |

Argparse usage failures also exit **2**, but print usage to stderr rather than a CRITICAL health report. JSON input failures produce `{status: "UNKNOWN", exit_code: 3, error: ...}` on stdout. Valid empty data produces a normal UNKNOWN report with counters.

- Ready requires phase `Running`, a Pod `Ready` condition with string status `True`, and no deletion timestamp. Missing optional conditions mean not ready. This snapshot does not independently verify a live probe or readiness gate.
- Succeeded pods count as completed and do not affect readiness or restart health checks. All other phases, including Failed, are evaluated.
- Restart totals include ordinary and init-container status arrays, once per record. They are **cumulative**, not restart rates and not necessarily restarts in the event window. Thresholds apply per pod, not the whole namespace; threshold 0 intentionally flags every evaluated pod.
- Event timestamp precedence: `series.lastObservedTime`, `lastTimestamp`, `eventTime`, `metadata.creationTimestamp`. Try the next candidate when one is invalid. Convert offsets to UTC. Include exact lower/upper bounds; exclude future events. Count records, not historical `count` values.
- Warning records without a usable timestamp appear in diagnostics. Unless an already-known critical condition wins, they make recency assessment UNKNOWN rather than silently healthy.
- Pending-only or terminating-only namespaces can be transient, but the zero-ready policy deliberately flags them CRITICAL. The reasons make this choice visible.
- Snapshot structure and resource namespace membership are validated first. Resource details are validated only within the selected namespace. Conflicting or duplicate Ready conditions are invalid. Optional event timestamps/series are interpreted only for selected Warning events. Unknown additional fields are ignored. Custom files have a 16 MiB limit. Nonstandard JSON constants (`NaN`, `Infinity`, `-Infinity`) are rejected even in unused fields.

## Fixture shape

See the complete examples in `ns_health/data/`.

```json
{
  "metadata": {
    "referenceTime": "2026-11-10T12:00:00Z",
    "namespaces": ["demo", "other"]
  },
  "pods": {"apiVersion": "v1", "kind": "PodList", "items": []},
  "events": {"apiVersion": "v1", "kind": "EventList", "items": []}
}
```

Pod records require metadata name/namespace and a supported status phase. Container statuses, when present, require a name and a nonnegative integer `restartCount`. Events require metadata name/namespace and type. An explicit namespace list distinguishes a known empty namespace from a name not present in the simulation.

## Tests and coverage

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_stdlib_coverage.py
```

The packaging test builds a wheel, installs it using `--no-index` into a fresh venv, and runs all four scenarios and the installed console script from another working directory. It takes several seconds and needs Python's standard `venv`/`ensurepip` support.

The stdlib script records **executed-line coverage**, not coverage.py statement or branch coverage. For the original PRD's formal 85% statement target, install the development dependency in a network-enabled environment:

```bash
.venv/bin/python -m pip install 'coverage>=7.6'
.venv/bin/python -m coverage run --source=ns_health -m unittest discover -s tests -v
.venv/bin/python -m coverage report -m --fail-under=85
```

See [validation results](docs/VALIDATION.md) for measured statement and branch coverage.

GitHub Actions configures the formal statement check for Python 3.11, 3.12, 3.13 and 3.14, with a 10-minute job limit. A workflow file is not evidence of a successful remote run. See `docs/VALIDATION.md` for actual local checks and current limitations.

## Project map

- `ns_health/health.py`: validation, time selection, counters and decisions.
- `ns_health/cli.py`: flags, fixture loading, output and exit handling.
- `ns_health/data/`: deterministic scenarios, including other-namespace distractors.
- `tests/`: business-rule, CLI and offline installation checks.
- `scripts/`: offline wheel builder and standard-library coverage helper.
- `docs/`: PRD, design, test table, real evidence and demo instructions.

## Submission and learning

Review the code and rehearse the demonstration in `docs/DEMO.md` before mentor review.

Official references:

- [kubectl plugin conventions](https://kubernetes.io/docs/tasks/extend-kubectl/kubectl-plugins/)
- [Pod lifecycle and conditions](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Readiness and liveness probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)

License: MIT. To clean a local setup, delete only this project's `.venv`, generated coverage files and `dist` if rebuilding; do not remove source or your evidence.
