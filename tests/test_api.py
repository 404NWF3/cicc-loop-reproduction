from fastapi.testclient import TestClient

from loop_research.api import create_app
from loop_research.config import Settings


def test_api_lifecycle_validation_and_local_configuration(tmp_path):
    settings = Settings(
        _env_file=None,
        state_dir=tmp_path,
        data_dir=tmp_path / "data",
        worker_autostart=False,
        deepseek_api_key="test-only-sentinel",
        deepseek_model="test-model",
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health").json()["worker"] == "offline"
        response = client.post("/api/v1/runs", json={"name": "test", "rounds": 1})
        assert response.status_code == 201
        run = response.json()
        assert client.post(f"/api/v1/runs/{run['id']}/start").json()["state"] == "queued"
        assert client.post(f"/api/v1/runs/{run['id']}/pause").json()["state"] == "paused"
        assert client.get(f"/api/v1/runs/{run['id']}/report").json()["is_experiment"] is False
        assert client.get("/api/v1/datasets").json() == {"items": []}
        assert client.get("/api/v1/experiments").json()["status"] == "not_run"
        check = client.post("/api/v1/models/check")
        assert check.json()["remote_check_performed"] is False
        assert "test-only-sentinel" not in check.text
        assert "test-only-sentinel" not in client.get("/api/v1/capabilities").text
        assert client.post("/api/v1/runs", json={"rounds": 0}).status_code == 422
        valid = client.post("/api/v1/factors/debug", json={"expression": "ts_mean(gap, 5)"})
        assert valid.json()["lookback"] == 5 and valid.json()["metrics"] is None
        invalid = client.post("/api/v1/factors/debug", json={"expression": "__import__('os')"})
        assert invalid.status_code == 422 and invalid.json()["code"] == "invalid_expression"
        assert client.get("/api/v1/missing").status_code == 404
        assert (
            client.post(
                "/api/v1/runs", json={}, headers={"Origin": "https://unrelated.example"}
            ).status_code
            == 403
        )
    assert settings.database_path == tmp_path / "loop.sqlite3"


def test_spa_refresh_never_masks_unknown_api_or_asset_routes(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><main>fixture app</main></html>")
    settings = Settings(
        _env_file=None, state_dir=tmp_path / "state", web_dist=dist, worker_autostart=False
    )
    with TestClient(create_app(settings)) as client:
        assert "fixture app" in client.get("/console/runs/example").text
        assert client.get("/api/v1/missing").status_code == 404
        assert client.get("/assets/missing.js").status_code == 404
