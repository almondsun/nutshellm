import time

from fastapi.testclient import TestClient
from nutshellm.api import create_app
from nutshellm.config import Settings
from nutshellm.schemas import (
    ModelAnswer,
    ModelUsage,
    RunMode,
    RunResult,
    SavingsMetrics,
    ValidationResult,
)


class FakeEngine:
    async def run(self, run_id, request):
        answer = ModelAnswer(
            text="validated answer",
            usage=ModelUsage(input_tokens=80, output_tokens=10),
        )
        return RunResult(
            run_id=run_id,
            scenario_id=request.scenario_id,
            mode=RunMode.COMPARE,
            task="task",
            baseline=answer,
            optimized=answer,
            final_segments=[],
            attempts=[],
            validation=ValidationResult(
                status="passed", score=1, reason="fixture"
            ),
            fallback=None,
            metrics=SavingsMetrics(
                original_input_tokens=100,
                optimized_input_tokens=80,
                paritok_tokens_saved=20,
                directly_pruned_tokens=0,
                total_tokens_saved=20,
                savings_percent=20,
                estimated_input_cost_saved_usd=0,
                estimated_total_run_cost_usd=0,
                total_latency_ms=5,
            ),
        )


def test_create_poll_and_content_free_metrics(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "api.sqlite3"),
        per_ip_daily_run_limit=2,
    )
    app = create_app(settings, engine=FakeEngine())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/runs", json={"scenario_id": "retry-cache-bug"}
        )
        assert created.status_code == 202
        job_id = created.json()["id"]
        for _ in range(30):
            response = client.get(f"/api/v1/runs/{job_id}")
            if response.json()["status"] == "complete":
                break
            time.sleep(0.02)
        assert response.status_code == 200
        assert response.json()["result"]["validation"]["status"] == "passed"
        metrics = client.get("/api/v1/metrics/summary").json()
        assert metrics["runs"] == 1
        assert "task" not in metrics


def test_unknown_scenario_does_not_enter_queue(tmp_path):
    app = create_app(
        Settings(database_path=str(tmp_path / "api.sqlite3")),
        engine=FakeEngine(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs", json={"scenario_id": "not-real"}
        )
    assert response.status_code == 404


def test_run_result_is_bound_to_anonymous_session(tmp_path):
    app = create_app(
        Settings(database_path=str(tmp_path / "api.sqlite3")),
        engine=FakeEngine(),
    )
    with TestClient(app) as owner:
        created = owner.post(
            "/api/v1/runs", json={"scenario_id": "retry-cache-bug"}
        )
        job_id = created.json()["id"]
        assert owner.get(f"/api/v1/runs/{job_id}").status_code == 200
    with TestClient(app) as stranger:
        assert stranger.get(f"/api/v1/runs/{job_id}").status_code == 404


def test_frontend_dist_path_is_deployment_configurable(tmp_path, monkeypatch):
    frontend = tmp_path / "web"
    frontend.mkdir()
    (frontend / "index.html").write_text("<h1>nutsheLLM</h1>")
    monkeypatch.setenv("FRONTEND_DIST", str(frontend))
    app = create_app(
        Settings(database_path=str(tmp_path / "api.sqlite3")),
        engine=FakeEngine(),
    )
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "nutsheLLM" in response.text


def test_chunked_oversized_body_is_rejected_before_json_parsing(tmp_path):
    app = create_app(
        Settings(database_path=str(tmp_path / "api.sqlite3"), max_context_chars=10),
        engine=FakeEngine(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs",
            content=(b"x" * 20_000 for _ in range(2)),
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 413
