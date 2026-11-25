# Run and test

Open Terminal in the extracted `kubectl-namespace-health` folder. Requires Python 3.11 or newer. These macOS/zsh commands also work on Linux.

## Quick source run

```bash
python3 --version
python3 -m ns_health --help
python3 -m ns_health --scenario healthy
python3 -m unittest discover -s tests -v
```

The final local result is 50 passing tests. Installation testing needs standard Python venv/ensurepip support; no cluster is required.

## Local offline installation

```bash
python3 scripts/build_wheel.py
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --no-index --force-reinstall dist/kubectl_namespace_health-1.0.0-py3-none-any.whl
kubectl-ns_health --scenario healthy
```

The runtime has no third-party dependencies. Activating this environment affects only the current terminal. Leave it with `deactivate` when finished. Rebuild the wheel after changing the source, then reinstall with the command above.

## All scenarios and exit codes

```bash
for scenario in healthy degraded critical empty; do
  python -m ns_health --scenario "$scenario"
  result=$?
  echo "Scenario $scenario returned $result"
done
```

| Scenario | Expected status | Expected exit |
|---|---|---:|
| healthy | HEALTHY | 0 |
| degraded | DEGRADED | 1 |
| critical | CRITICAL | 2 |
| empty | UNKNOWN | 3 |

Nonzero scenario exits are intentional. Run the loop in a normal shell without `set -e`; do not join scenario commands using `&&`.

## JSON, custom fixtures and options

```bash
python -m ns_health --scenario degraded --json
python -m ns_health --fixture ns_health/data/healthy.json -n demo --json
python -m ns_health --scenario healthy --restart-threshold 0
python -m ns_health --scenario degraded --recent-minutes 10
python -m ns_health --scenario degraded --now 2026-11-10T14:00:00Z
```

`--fixture` and `--scenario` are mutually exclusive. Invalid fixtures/unknown namespaces exit 3; invalid command usage exits 2 with usage text on stderr. The report always identifies simulated data and the effective reference clock.

## Tests and executed-line coverage

```bash
python -m unittest discover -s tests -v
python scripts/check_stdlib_coverage.py
```

The trace helper writes its separate executed-line measurement to `docs/evidence/stdlib_coverage.json`.

## Formal coverage (requires a dependency download)

With the virtual environment active and internet access:

```bash
python -m pip install 'coverage>=7.6'
python -m coverage run --source=ns_health -m unittest discover -s tests -v
python -m coverage report -m --fail-under=85
```

The final command enforces the 85% statement target.

Optional branch measurement, kept separate so the statement report remains reproducible:

```bash
python -m coverage run --branch --data-file=.coverage.branch --source=ns_health -m unittest discover -s tests -v
python -m coverage report --data-file=.coverage.branch -m --fail-under=85
```

The branch-enabled report combines statements and branches; label it accordingly.

## kubectl integration

Only if kubectl is already installed, in the activated venv:

```bash
kubectl plugin list --name-only
kubectl ns-health --scenario healthy -n demo
kubectl ns-health --scenario critical --json
```

These commands exercise local plugin execution with fixture data. No Kubernetes cluster is contacted. If a new terminal cannot find the command, activate this project's `.venv` there first.

See `docs/VALIDATION.md` for measured results and `docs/DEMO.md` for the demo script.