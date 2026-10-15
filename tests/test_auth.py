import base64

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from loop_research.api import create_app
from loop_research.config import Settings

USERNAME = "research"
PASSWORD = "test-only-unique-password"


@pytest.fixture
def secured_client(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>private console</html>")
    (dist / "app.js").write_text("// private asset")
    settings = Settings(
        _env_file=None,
        state_dir=tmp_path / "state",
        data_dir=tmp_path / "data",
        web_dist=dist,
        worker_autostart=False,
        auth_required=True,
        auth_username=USERNAME,
        auth_password=PASSWORD,
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/console",
        "/app.js",
        "/docs",
        "/openapi.json",
        "/api/v1/capabilities",
        "/api/v1/runs",
        "/api/v1/runs/example/report",
        "/api/v1/runs/example/events",
    ],
)
def test_all_pages_and_api_routes_require_auth(secured_client, path):
    response = secured_client.get(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic ")
    assert response.headers["cache-control"] == "no-store"
    assert PASSWORD not in response.text


@pytest.mark.parametrize(
    "header",
    [
        "Bearer example",
        "Basic %invalid",
        "Basic",
        "Basic " + base64.b64encode(b"missing-separator").decode(),
        "Basic " + base64.b64encode(b"research:wrong-password").decode(),
        "Basic " + base64.b64encode(f"wrong-user:{PASSWORD}".encode()).decode(),
    ],
)
def test_bad_credentials_cannot_create_tasks(secured_client, header):
    response = secured_client.post("/api/v1/runs", json={}, headers={"Authorization": header})
    assert response.status_code == 401
    assert secured_client.get("/api/v1/runs", auth=(USERNAME, PASSWORD)).json() == {"items": []}


def test_valid_auth_serves_spa_assets_and_controls_tasks(secured_client):
    secured_client.auth = (USERNAME, PASSWORD)
    assert "private console" in secured_client.get("/console/run/example").text
    assert "private asset" in secured_client.get("/app.js").text
    response = secured_client.post("/api/v1/runs", json={}, headers={"Origin": "http://testserver"})
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    run_id = response.json()["id"]
    assert secured_client.post(f"/api/v1/runs/{run_id}/start").json()["state"] == "queued"
    assert PASSWORD not in secured_client.get("/api/v1/capabilities").text


@pytest.mark.parametrize("origin", ["https://evil.example", "http://127.0.0.1:5173", "null"])
def test_production_rejects_cross_origin_control_even_with_credentials(secured_client, origin):
    response = secured_client.post(
        "/api/v1/runs", json={}, auth=(USERNAME, PASSWORD), headers={"Origin": origin}
    )
    assert response.status_code == 403


def test_only_get_health_is_public(secured_client):
    assert secured_client.get("/api/v1/health").status_code == 200
    assert secured_client.post("/api/v1/health").status_code == 401
    assert secured_client.get("/api/v1/health/other").status_code == 401


def test_health_is_unavailable_until_required_worker_has_a_lease(tmp_path):
    settings = Settings(_env_file=None, state_dir=tmp_path, worker_autostart=True)
    # No lifespan startup: simulates a required worker that has not acquired a lease.
    client = TestClient(create_app(settings))
    assert client.get("/api/v1/health").status_code == 503
    client.app.state.store.acquire_worker("test-worker")
    assert client.get("/api/v1/health").status_code == 200
    client.app.state.store.release_worker("test-worker")
    assert client.get("/api/v1/health").status_code == 503


@pytest.mark.parametrize(
    "values",
    [
        {"auth_required": True},
        {"auth_username": USERNAME},
        {"auth_password": PASSWORD},
        {"auth_username": USERNAME, "auth_password": "short"},
        {"auth_username": "bad:user", "auth_password": PASSWORD},
        {"auth_username": "bad user", "auth_password": PASSWORD},
        {"auth_username": "bad\u00a0user", "auth_password": PASSWORD},
        {"auth_username": "bad\u007fuser", "auth_password": PASSWORD},
    ],
)
def test_invalid_auth_configuration_fails_without_leaking_password(values):
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, **values)
    assert PASSWORD not in str(exc.value)


def test_password_is_redacted_in_settings():
    settings = Settings(_env_file=None, auth_username=USERNAME, auth_password=PASSWORD)
    assert PASSWORD not in repr(settings)
    assert PASSWORD not in settings.model_dump_json()
