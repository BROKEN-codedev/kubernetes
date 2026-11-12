import copy
import unittest

from ns_health.health import InputError, analyze
from tests.common import event, pod, snapshot


class HealthTests(unittest.TestCase):
    def test_healthy_counts_and_truthful_source(self):
        r = analyze(snapshot())
        self.assertEqual(r.get("status"), "HEALTHY")
        self.assertEqual(r["exit_code"], 0)
        self.assertEqual(r["summary"], {"total_pods": 1, "completed_pods": 0, "evaluated_pods": 1,
                                      "ready_pods": 1, "not_ready_pods": 0, "total_restarts": 0,
                                      "recent_warning_records": 0})
        self.assertEqual(r["source"], "simulation")
        self.assertEqual(r["reference_time"], "2026-11-10T12:00:00+00:00")

    def test_unready_pod_does_not_hide_behind_running(self):
        r = analyze(snapshot([pod(), pod("worker", ready="False")]))
        self.assertEqual(r.get("status"), "DEGRADED")
        self.assertEqual(r["summary"]["not_ready_pods"], 1)

    def test_missing_conditions_and_deleting_pod_not_ready(self):
        for mode in ["missing", "deleting"]:
            with self.subTest(mode=mode):
                p = pod("worker")
                if mode == "missing":
                    del p["status"]["conditions"]
                else:
                    p["metadata"]["deletionTimestamp"] = "2026-11-10T11:59:00Z"
                self.assertEqual(analyze(snapshot([pod(), p])).get("status"), "DEGRADED")

    def test_no_ready_failed_and_waiting_reasons_are_critical(self):
        cases = [pod(ready="False"), pod(phase="Failed"), pod(phase="Pending")]
        for reason in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
            p = pod("broken")
            p["status"]["containerStatuses"][0]["state"] = {"waiting": {"reason": reason}}
            cases.append(p)
        for p in cases:
            with self.subTest(p=p):
                self.assertEqual(analyze(snapshot([p])).get("status"), "CRITICAL")

    def test_completed_pods_do_not_distort_readiness_or_restarts(self):
        r = analyze(snapshot([pod(), pod("job", phase="Succeeded", restarts=99)]))
        self.assertEqual(r.get("status"), "HEALTHY")
        self.assertEqual(r["summary"]["completed_pods"], 1)
        self.assertEqual(r["summary"]["total_restarts"], 0)

    def test_empty_and_all_completed_are_unknown(self):
        for pods in [[], [pod(phase="Succeeded")]]:
            self.assertEqual(analyze(snapshot(pods)).get("status"), "UNKNOWN")

    def test_restart_counts_include_init_and_every_container_once(self):
        p = pod(restarts=2)
        p["status"]["containerStatuses"].append({"name": "sidecar", "restartCount": 1})
        p["status"]["initContainerStatuses"] = [{"name": "init", "restartCount": 2}]
        r = analyze(snapshot([p]))
        self.assertEqual(r.get("status"), "DEGRADED")
        self.assertEqual(r["summary"]["total_restarts"], 5)

    def test_threshold_boundaries_are_per_pod(self):
        for restarts, expected in [(4, "HEALTHY"), (5, "DEGRADED"), (6, "DEGRADED")]:
            self.assertEqual(analyze(snapshot([pod(restarts=restarts)])).get("status"), expected)
        self.assertEqual(analyze(snapshot([pod("a", restarts=3), pod("b", restarts=3)])).get("status"), "HEALTHY")
        self.assertEqual(analyze(snapshot(), restart_threshold=0).get("status"), "DEGRADED")

    def test_namespace_filters_both_resources(self):
        r = analyze(snapshot([pod(), pod("bad", "other", phase="Failed")], [event(namespace="other")]))
        self.assertEqual(r.get("status"), "HEALTHY")
        self.assertEqual(r["summary"]["total_pods"], 1)
        self.assertEqual(r["summary"]["recent_warning_records"], 0)

    def test_unknown_namespace_is_not_an_empty_namespace(self):
        with self.assertRaises(InputError):
            analyze(snapshot(), "absent")
        self.assertEqual(analyze(snapshot(), "other").get("status"), "UNKNOWN")

    def test_missing_optional_container_statuses_is_safe(self):
        p = pod()
        del p["status"]["containerStatuses"]
        self.assertEqual(analyze(snapshot([p])).get("status"), "HEALTHY")

    def test_analysis_does_not_modify_input(self):
        data = snapshot([pod("z"), pod("a")], [event()])
        before = copy.deepcopy(data)
        r = analyze(data)
        self.assertEqual(r.get("status"), "DEGRADED")
        self.assertEqual(data, before)
        self.assertEqual([p["name"] for p in r["pods"]], ["a", "z"])

    def test_invalid_required_structures_are_rejected(self):
        invalid = [None, [], {}, snapshot()]
        invalid[-1]["pods"]["items"] = "not a list"
        for key, value in [("metadata", []), ("events", []), ("pods", None)]:
            d = snapshot(); d[key] = value; invalid.append(d)
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(InputError):
                analyze(data)

    def test_invalid_metadata_phase_and_conditions_are_rejected(self):
        invalid = []
        for change in [lambda p: p.pop("metadata"), lambda p: p["metadata"].update(namespace="missing"),
                       lambda p: p["status"].update(phase="Invented"), lambda p: p["status"].pop("phase"),
                       lambda p: p["status"].update(conditions="wrong"),
                       lambda p: p["status"].update(containerStatuses=[{}])]:
            p = pod(); change(p); invalid.append(snapshot([p]))
        for d in invalid:
            with self.subTest(d=d), self.assertRaises(InputError): analyze(d)

    def test_invalid_restart_counts_and_status_arrays_are_rejected(self):
        for value in [-1, 1.5, True, "2"]:
            p = pod(restarts=value)
            with self.subTest(value=value), self.assertRaises(InputError): analyze(snapshot([p]))
        p = pod(); p["status"]["containerStatuses"] = {}
        with self.assertRaises(InputError): analyze(snapshot([p]))

    def test_invalid_options_and_naive_times_are_rejected(self):
        for opts in [{"recent_minutes": 0}, {"restart_threshold": -1}, {"now": "2026-11-10T12:00:00"},
                     {"now": "not a time"}, {"recent_minutes": True}]:
            with self.subTest(opts=opts), self.assertRaises(InputError): analyze(snapshot(), **opts)

    def test_failed_pod_still_critical_when_another_pod_is_ready(self):
        r = analyze(snapshot([pod(), pod("failed-job", phase="Failed")]))
        self.assertEqual(r["status"], "CRITICAL")
        self.assertEqual(r["summary"]["ready_pods"], 1)
        self.assertEqual(r["summary"]["not_ready_pods"], 1)
        self.assertIn("failed-job: pod phase Failed", r["reasons"])

    def test_duplicate_namespaces_pods_and_container_records_are_rejected(self):
        namespaces = snapshot()
        namespaces["metadata"]["namespaces"].append("demo")
        containers = snapshot()
        containers["pods"]["items"][0]["status"]["containerStatuses"].append(
            {"name": "app", "restartCount": 0})
        for data in (namespaces, snapshot([pod(), pod()]), containers):
            with self.subTest(data=data), self.assertRaises(InputError):
                analyze(data)

    def test_malformed_conditions_and_resource_kinds_are_rejected(self):
        condition = snapshot()
        condition["pods"]["items"][0]["status"]["conditions"][0]["status"] = True
        kind = snapshot()
        kind["events"]["kind"] = "PodList"
        message = snapshot(events=[event()])
        message["events"]["items"][0]["message"] = 123
        for data in (condition, kind, message):
            with self.subTest(data=data), self.assertRaises(InputError):
                analyze(data)

    def test_warning_window_outside_supported_date_range_is_rejected(self):
        for opts in ({"recent_minutes": 10**30}, {"now": "0001-01-01T00:00:00Z"}):
            with self.subTest(opts=opts), self.assertRaises(InputError):
                analyze(snapshot(), **opts)


class EventTests(unittest.TestCase):
    def test_window_includes_both_bounds_but_not_old_or_future(self):
        events = [event("lower", "2026-11-10T11:00:00Z"), event("upper", "2026-11-10T12:00:00Z"),
                  event("old", "2026-11-10T10:59:59Z"), event("future", "2026-11-10T12:00:01Z")]
        r = analyze(snapshot(events=events))
        self.assertEqual(r.get("status"), "DEGRADED")
        self.assertEqual(r["summary"]["recent_warning_records"], 2)
        self.assertEqual([e["name"] for e in r["recent_warning_events"]], ["lower", "upper"])

    def test_timezone_and_count_field(self):
        r = analyze(snapshot(events=[event(stamp="2026-11-10T17:00:00+05:30")]))
        self.assertEqual(r.get("summary", {}).get("recent_warning_records"), 1)

    def test_series_precedence_over_last_timestamp(self):
        e = event(stamp="2026-11-10T10:00:00Z")
        e["series"] = {"lastObservedTime": "2026-11-10T11:45:00Z", "count": 500}
        self.assertEqual(analyze(snapshot(events=[e])).get("summary", {}).get("recent_warning_records"), 1)

    def test_invalid_timestamp_tries_valid_fallback(self):
        for key in ["lastTimestamp", "eventTime", "creationTimestamp"]:
            e = event(stamp="invalid")
            if key == "lastTimestamp": e["lastTimestamp"] = "2026-11-10T11:20:00Z"
            elif key == "eventTime": e["eventTime"] = "2026-11-10T11:20:00Z"
            else: e["metadata"][key] = "2026-11-10T11:20:00Z"
            e["series"] = {"lastObservedTime": "invalid"}
            self.assertEqual(analyze(snapshot(events=[e])).get("summary", {}).get("recent_warning_records"), 1)

    def test_unusable_warning_timestamps_are_reported(self):
        r = analyze(snapshot(events=[event(stamp="invalid"), event("normal", type_="Normal")]))
        self.assertEqual(r.get("summary", {}).get("recent_warning_records"), 0)
        self.assertEqual(r["timestamp_diagnostics"]["unusable_warning_records"], ["warning"])

    def test_unknown_warning_recency_takes_precedence_over_degraded(self):
        r = analyze(snapshot([pod(restarts=5)], [event(stamp="invalid")]))
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertEqual(r["exit_code"], 3)
        self.assertEqual(r["summary"]["total_restarts"], 5)
        self.assertIn("Warning event recency cannot be determined", r["reasons"])
        self.assertEqual(r["timestamp_diagnostics"]["unusable_warning_records"], ["warning"])

    def test_critical_evidence_wins_over_unknown_warning_recency(self):
        r = analyze(snapshot([pod(), pod("failed", phase="Failed")], [event(stamp="invalid")]))
        self.assertEqual(r["status"], "CRITICAL")
        self.assertEqual(r["exit_code"], 2)
        self.assertIn("failed: pod phase Failed", r["reasons"])
        self.assertEqual(r["timestamp_diagnostics"]["unusable_warning_records"], ["warning"])

    def test_unusable_timestamp_does_not_cross_namespace_or_event_type(self):
        normal = event("normal", stamp="invalid", type_="Normal")
        normal["series"] = "unused malformed optional field"
        foreign = event("foreign", stamp="invalid", namespace="other")
        foreign["series"] = None
        r = analyze(snapshot(events=[normal, foreign]))
        self.assertEqual(r["status"], "HEALTHY")
        self.assertEqual(r["timestamp_diagnostics"]["unusable_warning_records"], [])

    def test_override_now_is_used(self):
        r = analyze(snapshot(events=[event()]), now="2026-11-10T14:00:00Z")
        self.assertEqual(r.get("status"), "HEALTHY")
        self.assertEqual(r["reference_time"], "2026-11-10T14:00:00+00:00")
