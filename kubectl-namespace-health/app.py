"""HTTP and static web adapter for the existing offline analyzer."""

import json
from importlib.resources import files
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ns_health.cli import reject_json_constant
from ns_health.health import InputError, analyze


Scenario = Literal["healthy", "degraded", "critical", "empty"]
REQUEST_LIMIT = 4 * 1024 * 1024
WEB_ROOT = Path(__file__).resolve().with_name("web")

app = FastAPI(title="Namespace Health API", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="assets")


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    scenario: Scenario | None = None
    fixture: str | None = None
    namespace: str = Field(default="demo", min_length=1)
    recent_minutes: int = Field(default=60, gt=0)
    restart_threshold: int = Field(default=5, ge=0)
    now: str | None = None


def load_scenario(scenario: Scenario) -> dict:
    fixture = files("ns_health").joinpath("data", scenario + ".json").read_text(encoding="utf-8")
    return json.loads(fixture, parse_constant=reject_json_constant)


@app.get("/", include_in_schema=False)
def workspace() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/guide", include_in_schema=False)
def guide() -> FileResponse:
    return FileResponse(WEB_ROOT / "guide.html")


@app.get("/api/scenarios/{scenario}")
def scenario_metadata(scenario: Scenario) -> dict:
    return load_scenario(scenario)["metadata"]


@app.post("/api/analyze")
async def analyze_snapshot(request: Request) -> dict:
    # Leave room for the platform's HTTP payload limit and enforce the same cap locally.
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > REQUEST_LIMIT:
            raise HTTPException(413, "Analysis request exceeds 4 MiB.")
        body.extend(chunk)
    try:
        options = AnalysisRequest.model_validate_json(body)
    except ValidationError as exc:
        first = exc.errors(include_input=False)[0]
        field = ".".join(map(str, first["loc"])) or "request"
        raise HTTPException(422, f"{field}: {first['msg']}") from exc
    if (options.scenario is None) == (options.fixture is None):
        raise HTTPException(422, "Choose one scenario or provide one JSON snapshot.")
    if options.fixture is not None:
        try:
            snapshot = json.loads(options.fixture, parse_constant=reject_json_constant)
        except (ValueError, RecursionError) as exc:
            raise HTTPException(422, f"Invalid snapshot JSON: {exc}") from exc
    else:
        snapshot = load_scenario(options.scenario)
    try:
        return analyze(snapshot, options.namespace, options.recent_minutes,
                       options.restart_threshold, options.now)
    except InputError as exc:
        raise HTTPException(422, str(exc)) from exc
