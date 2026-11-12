"""Pure analysis of a validated, simulated Kubernetes snapshot."""

from datetime import datetime, timedelta, timezone
from typing import Any


class InputError(ValueError):
    """A snapshot or analysis option cannot be interpreted safely."""


def object_(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise InputError(f"{label} must be an object")
    return value


def array(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise InputError(f"{label} must be an array")
    return value


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{label} must be a nonempty string")
    return value


def integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InputError(f"{label} must be an integer >= {minimum}")
    return value


def parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(text(value, "timestamp").replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise InputError("timestamp must be valid ISO 8601 with a timezone") from exc


def resource_metadata(resource: dict, namespaces: list[str], label: str) -> dict:
    metadata = object_(resource.get("metadata"), f"{label}.metadata")
    text(metadata.get("name"), f"{label}.metadata.name")
    namespace = text(metadata.get("namespace"), f"{label}.metadata.namespace")
    if namespace not in namespaces:
        raise InputError(f"{label} refers to undeclared namespace {namespace!r}")
    return metadata


def resource_items(data: dict, key: str, kind: str) -> list[dict]:
    resource = object_(data.get(key), key)
    if resource.get("apiVersion") != "v1" or resource.get("kind") != kind:
        raise InputError(f"{key} must be a core/v1 {kind}")
    return array(resource.get("items"), f"{key}.items")


def pod_detail(pod: dict, namespaces: list[str]) -> dict:
    pod = object_(pod, "pod")
    meta = resource_metadata(pod, namespaces, "pod")
    status = object_(pod.get("status"), "pod.status")
    phase = status.get("phase")
    if phase not in ("Pending", "Running", "Succeeded", "Failed", "Unknown"):
        raise InputError("pod.status.phase is missing or unsupported")
    conditions = array(status.get("conditions", []), "pod.status.conditions")
    ready = False
    for raw in conditions:
        condition = object_(raw, "pod condition")
        text(condition.get("type"), "condition.type")
        if condition.get("status") not in ("True", "False", "Unknown"):
            raise InputError("condition.status must be True, False or Unknown as a string")
        if condition["type"] == "Ready":
            ready = condition["status"] == "True"
    deleting = meta.get("deletionTimestamp") is not None
    if deleting:
        parse_time(meta["deletionTimestamp"])
    restarts = 0
    waiting = []
    for key in ("containerStatuses", "initContainerStatuses"):
        names = set()
        for raw in array(status.get(key, []), f"pod.status.{key}"):
            container = object_(raw, "container status")
            name = text(container.get("name"), "container.name")
            if name in names:
                raise InputError(f"duplicate container status: {name}")
            names.add(name)
            restarts += integer(container.get("restartCount"), "container.restartCount")
            state = object_(container.get("state", {}), "container.state")
            if "waiting" in state:
                info = object_(state["waiting"], "container.state.waiting")
                if info.get("reason") is not None:
                    waiting.append(text(info["reason"], "waiting.reason"))
    return {"name": meta["name"], "namespace": meta["namespace"], "phase": phase,
            "ready": phase == "Running" and ready and not deleting, "terminating": deleting,
            "restarts": restarts, "waiting_reasons": sorted(waiting)}


def warning_time(event: dict) -> datetime | None:
    series = object_(event.get("series", {}), "event.series")
    candidates = (series.get("lastObservedTime"), event.get("lastTimestamp"),
                  event.get("eventTime"), event["metadata"].get("creationTimestamp"))
    for value in candidates:
        if value is not None:
            try:
                return parse_time(value)
            except InputError:
                continue
    return None


def analyze(data: dict, namespace: str = "demo", recent_minutes: int = 60,
            restart_threshold: int = 5, now: str | None = None) -> dict:
    """Return deterministic evidence and a documented health decision.

    No input objects are changed and no external services are contacted.
    """
    data = object_(data, "snapshot")
    integer(recent_minutes, "recent_minutes", 1)
    integer(restart_threshold, "restart_threshold")
    meta = object_(data.get("metadata"), "snapshot.metadata")
    namespaces = array(meta.get("namespaces"), "metadata.namespaces")
    for name in namespaces:
        text(name, "namespace")
    if len(set(namespaces)) != len(namespaces):
        raise InputError("metadata.namespaces contains duplicates")
    text(namespace, "namespace option")
    if namespace not in namespaces:
        raise InputError(f"unknown namespace: {namespace}")
    reference = parse_time(meta.get("referenceTime"))
    if now is not None:
        reference = parse_time(now)
    try:
        lower = reference - timedelta(minutes=recent_minutes)
    except (OverflowError, ValueError) as exc:
        raise InputError("recent_minutes is outside the supported date range") from exc

    all_pods = [pod_detail(p, namespaces) for p in resource_items(data, "pods", "PodList")]
    identities = [(p["namespace"], p["name"]) for p in all_pods]
    if len(set(identities)) != len(identities):
        raise InputError("duplicate pod identity in snapshot")
    pods = sorted((p for p in all_pods if p["namespace"] == namespace), key=lambda p: p["name"])
    evaluated = [p for p in pods if p["phase"] != "Succeeded"]
    ready = sum(p["ready"] for p in evaluated)
    warnings, unusable = [], []
    for raw in resource_items(data, "events", "EventList"):
        event = object_(raw, "event")
        emeta = resource_metadata(event, namespaces, "event")
        event_type = text(event.get("type"), "event.type")
        for key in ("reason", "message"):
            if key in event:
                if not isinstance(event[key], str):
                    raise InputError(f"event.{key} must be a string")
        if emeta["namespace"] != namespace or event_type != "Warning":
            continue
        stamp = warning_time(event)
        if stamp is None:
            unusable.append(emeta["name"])
        elif lower <= stamp <= reference:
            warnings.append({"name": emeta["name"], "reason": event.get("reason", ""),
                             "message": event.get("message", ""), "timestamp": stamp.isoformat()})
    warnings.sort(key=lambda e: (e["timestamp"], e["name"]))
    critical = []
    for p in evaluated:
        if p["phase"] == "Failed":
            critical.append(f"{p['name']}: pod phase Failed")
        for reason in p["waiting_reasons"]:
            if reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                critical.append(f"{p['name']}: {reason}")
    if evaluated and not ready:
        critical.append("no evaluated pods are ready")
    degraded = []
    if ready < len(evaluated):
        degraded.append(f"{len(evaluated) - ready} pod(s) not ready")
    for p in evaluated:
        if p["restarts"] >= restart_threshold:
            degraded.append(f"{p['name']}: {p['restarts']} cumulative restarts >= {restart_threshold}")
    if warnings:
        degraded.append(f"{len(warnings)} recent Warning event record(s)")
    if critical:
        status, code, reasons = "CRITICAL", 2, critical + degraded
    elif not evaluated:
        status, code, reasons = "UNKNOWN", 3, ["no evaluated workloads (empty or completed only)"]
    elif unusable:
        status, code, reasons = "UNKNOWN", 3, ["Warning event recency cannot be determined"] + degraded
    elif degraded:
        status, code, reasons = "DEGRADED", 1, degraded
    else:
        status, code, reasons = "HEALTHY", 0, ["all evaluated pods ready; no configured health indicators triggered"]
    return {"status": status, "exit_code": code, "namespace": namespace, "source": "simulation",
            "reference_time": reference.isoformat(), "thresholds": {"recent_minutes": recent_minutes,
            "restart_threshold": restart_threshold}, "reasons": reasons,
            "summary": {"total_pods": len(pods), "completed_pods": len(pods) - len(evaluated),
            "evaluated_pods": len(evaluated), "ready_pods": ready, "not_ready_pods": len(evaluated) - ready,
            "total_restarts": sum(p["restarts"] for p in evaluated), "recent_warning_records": len(warnings)},
            "pods": pods, "recent_warning_events": warnings,
            "timestamp_diagnostics": {"unusable_warning_records": sorted(unusable)}}
