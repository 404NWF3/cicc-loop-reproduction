import json
from importlib.resources import files

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from loop_research.api import create_app
from loop_research.config import Settings
from loop_research.errors import ResearchError
from loop_research.live import budget_for, evaluator, manifest, model_stage
from loop_research.loop.runner import step
from loop_research.models.ledger import PersistentBudget
from loop_research.schemas import RunConfig
from loop_research.storage import Store


def test_live_recomputes_archived_evidence_and_resumes_without_duplicates(tmp_path):
    settings = Settings(_env_file=None, state_dir=tmp_path, budget_path=tmp_path / "budget.db")
    store = Store(settings.database_path, live_enabled=True)
    run = store.create(RunConfig(mode="live", rounds=1, batch_size=6, max_candidates=6))
    store.control(run["id"], "start")
    store.acquire_worker("one")
    for _ in range(2):
        step(store, "one", settings)
    store.control(run["id"], "pause")
    step(store, "one", settings)
    assert store.get(run["id"])["cursor"] == 2
    store.release_worker("one")
    restored = Store(settings.database_path, live_enabled=True)
    restored.control(run["id"], "resume")
    for _ in range(6):
        restored.acquire_worker("two")
        step(restored, "two", settings)
    final = restored.get(run["id"])
    assert final["state"] == "completed"
    assert final["counts"]["accepted"] == 6
    assert final["counts"]["model_calls"] == 0
    assert not settings.budget_path.exists()
    candidates = restored.candidates(run["id"])
    archive = json.loads(
        (files("loop_research.results") / "stocknet_flash_20261015_v2.json").read_text()
    )
    expected = {c["expression"]: c for c in archive["accepted_factors"]}
    assert len({c["fingerprint"] for c in candidates}) == 6
    for c in candidates:
        reference = expected[c["expression"]]
        assert c["origin"] == "archive_seed" and c["is_experiment"]
        assert c["discovery_ic"] == pytest.approx(reference["discovery_ic"], abs=1e-12)
        assert c["periods"]["selection"] == pytest.approx(reference["periods"]["selection"])
        assert c["series"][-1]["date"] == "2015-12-31"
        assert len(c["series"]) < 110
        assert all(g["status"] in {"passed", "not_applicable"} for g in c["gates"])
    assert candidates[0]["gates"][8]["status"] == "not_applicable"
    assert evaluator().panel["open"].index.max().year == 2015
    assert manifest()["holdout_included"] is False


@pytest.mark.parametrize("require_login", [False, True])
def test_paid_run_creation_and_every_control_require_server_token(tmp_path, require_login):
    settings = Settings(
        _env_file=None,
        state_dir=tmp_path,
        budget_path=tmp_path / "budget.db",
        worker_autostart=False,
        deepseek_api_key="private-key-sentinel",
        research_token="private-demo-token",
        auth_username="research" if require_login else "",
        auth_password="test-only-long-password" if require_login else "",
    )
    with TestClient(create_app(settings)) as client:
        if require_login:
            client.auth = ("research", "test-only-long-password")
        config = {"mode": "live", "generator": "deepseek", "rounds": 2, "batch_size": 6}
        assert client.post("/api/v1/runs", json=config).status_code == 401
        headers = {"X-Research-Token": "private-demo-token"}
        run = client.post("/api/v1/runs", json=config, headers=headers).json()
        for action in ["start", "pause", "stop", "resume"]:
            assert client.post(f"/api/v1/runs/{run['id']}/{action}").status_code == 401
        assert client.post(f"/api/v1/runs/{run['id']}/start", headers=headers).status_code == 200
        for path in ["/runs", "/capabilities", "/live/status", f"/runs/{run['id']}/report"]:
            response = client.get("/api/v1" + path)
            assert response.status_code == 200
            assert "private-key-sentinel" not in response.text
            assert "private-demo-token" not in response.text
        assert client.get("/api/v1/live/status").json()["budget"]["requests"] >= 50


def test_carried_budget_survives_reopen_and_preserves_unknown_requests(tmp_path):
    path = tmp_path / "ledger.db"
    ledger = PersistentBudget(path)
    ledger.carry_floor(50, 44836)
    ledger.reserve(2000)
    ledger.settle(2000, None)
    restored = PersistentBudget(path)
    restored.carry_floor(50, 44836)
    restored.carry_floor(50, 44836)
    assert restored.summary()["requests"] == 51
    assert restored.summary()["tokens_charged_or_reserved"] == 46836
    assert restored.summary()["unresolved_requests"] == 1
    restored.reserve(1000)
    restored.settle(1000, 600)
    assert restored.summary()["tokens_charged_or_reserved"] == 47436
    restored.carry_floor(52, 47436)
    assert restored.summary()["tokens_charged_or_reserved"] == 47436
    with pytest.raises(ResearchError, match="预算不足"):
        restored.reserve(120000)


def test_unknown_paid_phase_is_not_resubmitted_after_restart(tmp_path):
    settings = Settings(_env_file=None, state_dir=tmp_path, budget_path=tmp_path / "ledger.db")
    store = Store(settings.database_path, live_enabled=True)
    run = store.create(RunConfig(mode="live", generator="deepseek"))
    store.control(run["id"], "start")
    store.acquire_worker("worker")
    run = store.next_work("worker")
    store.checkpoint(run, {"model_phase": "generating"}, "worker", "request reserved")
    with pytest.raises(ResearchError, match="未重复请求"):
        model_stage(store, store.get(run["id"]), "worker", settings)
    assert not settings.budget_path.exists()


def test_live_limits_and_disabled_mode(tmp_path):
    for values in [
        {"max_candidates": 1201},
        {"rounds": 101, "batch_size": 12},
        {"max_seconds": 3601},
        {"max_model_cny": 11},
        {"batch_size": 13},
    ]:
        with pytest.raises(ValidationError):
            RunConfig(mode="live", **values)
    settings = Settings(
        _env_file=None, state_dir=tmp_path, live_enabled=False, worker_autostart=False
    )
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/runs", json={"mode": "live"}).status_code == 409


def test_live_budget_never_replaces_existing_experiment_usage(tmp_path):
    settings = Settings(_env_file=None, budget_path=tmp_path / "ledger.db")
    ledger = PersistentBudget(settings.budget_path)
    ledger.carry_floor(55, 90000)
    assert budget_for(settings).summary()["requests"] == 55
    assert budget_for(settings).summary()["tokens_charged_or_reserved"] == 90000


@pytest.mark.parametrize("require_login", [False, True])
def test_separate_frontend_origin_can_control_and_read_sse(tmp_path, require_login):
    settings = Settings(
        _env_file=None,
        state_dir=tmp_path,
        worker_autostart=False,
        cors_origins="https://demo.example",
        auth_username="research" if require_login else "",
        auth_password="test-only-long-password" if require_login else "",
    )
    with TestClient(create_app(settings)) as client:
        response = client.options(
            "/api/v1/runs",
            headers={
                "Origin": "https://demo.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-Research-Token",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "https://demo.example"
        assert response.headers["access-control-allow-credentials"] == "true"
        if require_login:
            denied = client.get(
                "/api/v1/runs", headers={"Origin": "https://demo.example"}
            )
            assert denied.status_code == 401
            assert denied.headers["access-control-allow-origin"] == "https://demo.example"
            client.auth = ("research", "test-only-long-password")
        assert (
            client.post(
                "/api/v1/runs", json={}, headers={"Origin": "https://demo.example"}
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/runs", json={}, headers={"Origin": "https://other.example"}
            ).status_code
            == 403
        )
