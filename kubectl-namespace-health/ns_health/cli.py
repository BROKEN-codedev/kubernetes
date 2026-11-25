"""Command-line interface; fixture mode never contacts a Kubernetes cluster."""

import argparse
from importlib.resources import files
import json
from pathlib import Path
import sys

from . import __version__
from .health import InputError, analyze

SCENARIOS = ("healthy", "degraded", "critical", "empty")


def reject_json_constant(value: str) -> None:
    """Reject the nonstandard numeric constants accepted by json.loads."""
    raise ValueError(f"{value} is not permitted in JSON")


def nonnegative(value: str) -> int:
    try:
        number = int(value)
        if number < 0:
            raise ValueError
        return number
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from exc


def positive(value: str) -> int:
    number = nonnegative(value)
    if number == 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kubectl-ns_health", description="Summarize namespace health from simulated pod and event data.")
    p.add_argument("-n", "--namespace", default="demo", help="namespace to summarize (default: demo)")
    source = p.add_mutually_exclusive_group()
    source.add_argument("--scenario", choices=SCENARIOS, help="bundled simulation (default: healthy)")
    source.add_argument("--fixture", type=Path, help="custom snapshot JSON path")
    p.add_argument("--json", action="store_true", help="write machine-readable JSON to stdout")
    p.add_argument("--recent-minutes", type=positive, default=60, help="Warning event window (default: 60)")
    p.add_argument("--restart-threshold", type=nonnegative, default=5, help="cumulative restarts per pod (default: 5)")
    p.add_argument("--now", help="override fixture reference time; ISO 8601 with timezone")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def render_text(report: dict) -> str:
    s = report["summary"]
    lines = [f"Namespace: {report['namespace']} | {report['status']} (exit {report['exit_code']})",
             f"Source: {report['source']} | Reference time: {report['reference_time']}",
             f"Pods: {s['total_pods']} total; {s['completed_pods']} completed; "
             f"{s['ready_pods']}/{s['evaluated_pods']} evaluated ready; {s['not_ready_pods']} not ready",
             f"Cumulative restarts: {s['total_restarts']} | Recent Warning records: {s['recent_warning_records']}",
             f"Restart threshold: {report['thresholds']['restart_threshold']} per pod | "
             f"Warning window: {report['thresholds']['recent_minutes']} minutes", "Reasons:"]
    lines.extend(f"  - {reason}" for reason in report["reasons"])
    if report["pods"]:
        lines.append("Pods:")
        for pod in report["pods"]:
            lines.append(f"  {pod['name']}: {pod['phase']}, ready={pod['ready']}, restarts={pod['restarts']}")
    if report["recent_warning_events"]:
        lines.append("Recent Warning events:")
        lines.extend(f"  {event['timestamp']} {event['name']}: {event['reason']} - {event['message']}"
                     for event in report["recent_warning_events"])
    unusable = report["timestamp_diagnostics"]["unusable_warning_records"]
    if unusable:
        lines.append("Warnings with unknown recency: " + ", ".join(unusable))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.fixture is not None:
            limit = 16 * 1024 * 1024
            if not args.fixture.is_file():
                raise InputError("fixture must be a readable regular file")
            with args.fixture.open("rb") as stream:
                payload = stream.read(limit + 1)
            if len(payload) > limit:
                raise InputError("fixture exceeds the 16 MiB input limit")
            content = payload.decode("utf-8")
        else:
            content = files("ns_health").joinpath("data", (args.scenario or "healthy") + ".json").read_text(encoding="utf-8")
        try:
            snapshot = json.loads(content, parse_constant=reject_json_constant)
        except ValueError as exc:
            # JSONDecodeError and Python's integer-digit limit are input failures.
            raise InputError(f"invalid JSON: {exc}") from exc
        report = analyze(snapshot, args.namespace, args.recent_minutes, args.restart_threshold, args.now)
    except (InputError, OSError, UnicodeError, RecursionError) as exc:
        message = str(exc)
        if args.json:
            print(json.dumps({"status": "UNKNOWN", "exit_code": 3, "namespace": args.namespace,
                              "source": "simulation", "error": message}, sort_keys=True))
        else:
            print(f"UNKNOWN: {message}", file=sys.stderr)
        return 3
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report))
    return report["exit_code"]
