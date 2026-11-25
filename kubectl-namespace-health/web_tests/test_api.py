import json
import unittest
from importlib.resources import files

from httpx import ASGITransport, AsyncClient

from app import app
from ns_health.health import analyze


class WebApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)

    async def test_pages_and_assets(self):
        for path in ("/", "/guide", "/assets/styles.css", "/assets/workspace.js"):
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status_code, 200)

    async def test_scenarios_match_python(self):
        for name, code in zip(("healthy", "degraded", "critical", "empty"), range(4)):
            with self.subTest(name=name):
                fixture = json.loads(files("ns_health").joinpath("data", name + ".json").read_text())
                response = await self.client.post("/api/analyze", json={"scenario": name})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), analyze(fixture))
                self.assertEqual(response.json()["exit_code"], code)

    async def test_custom_fixture_uses_selected_options(self):
        fixture = files("ns_health").joinpath("data", "degraded.json").read_text()
        response = await self.client.post("/api/analyze", json={
            "fixture": fixture, "namespace": "demo", "recent_minutes": 10,
            "restart_threshold": 8, "now": "2026-11-10T12:00:00Z",
        })
        self.assertEqual(response.json(), analyze(json.loads(fixture), "demo", 10, 8, "2026-11-10T12:00:00Z"))

    async def test_invalid_data_has_distinct_error(self):
        for source in ({"scenario": "empty", "namespace": "missing"}, {"fixture": "{"},
                       {"fixture": "NaN"}, {"scenario": "healthy", "fixture": "{}"},
                       {"scenario": "../health"}, {"scenario": "healthy", "restart_threshold": True}):
            with self.subTest(source=source):
                self.assertEqual((await self.client.post("/api/analyze", json=source)).status_code, 422)

    async def test_fixture_endpoint_returns_declared_namespaces(self):
        self.assertEqual((await self.client.get("/api/scenarios/degraded")).json()["namespaces"], ["demo", "other"])
        self.assertEqual((await self.client.get("/api/scenarios/missing")).status_code, 422)

    async def test_body_limit_rejects_before_parsing(self):
        response = await self.client.post("/api/analyze", content=b" " * (4 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)
