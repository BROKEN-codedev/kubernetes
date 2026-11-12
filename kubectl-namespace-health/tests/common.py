def pod(name="api", namespace="demo", phase="Running", ready="True", restarts=0):
    return {"metadata": {"name": name, "namespace": namespace}, "status": {
        "phase": phase, "conditions": [{"type": "Ready", "status": ready}],
        "containerStatuses": [{"name": "app", "ready": ready == "True", "restartCount": restarts}],
    }}


def event(name="warning", stamp="2026-11-10T11:30:00Z", namespace="demo", type_="Warning"):
    return {"metadata": {"name": name, "namespace": namespace}, "type": type_,
            "reason": "Unhealthy", "message": "Probe failed", "lastTimestamp": stamp, "count": 40}


def snapshot(pods=None, events=None):
    return {"metadata": {"referenceTime": "2026-11-10T12:00:00Z", "namespaces": ["demo", "other"]},
            "pods": {"apiVersion": "v1", "kind": "PodList", "items": [pod()] if pods is None else pods},
            "events": {"apiVersion": "v1", "kind": "EventList", "items": [] if events is None else events}}
