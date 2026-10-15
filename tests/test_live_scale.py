import json

import httpx
import pytest
from fastapi.testclient import TestClient

from loop_research.api import create_app
from loop_research.config import Settings
from loop_research.errors import ResearchError
from loop_research.loop.runner import step
from loop_research.models.deepseek import DeepSeekClient
from loop_research.models.ledger import PersistentBudget
from loop_research.schemas import RunConfig
from loop_research.storage import Store


@pytest.fixture
def model_run(tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None, state_dir=tmp_path, budget_path=tmp_path / "budget.db",
        worker_autostart=False, deepseek_api_key="mock-only-key",
    )
    requests = []
    crash_on = []

    def respond(request):
        if request.url.path == "/models":
            return httpx.Response(200, json={"data": [{"id": "deepseek-flash"}]})
        body = json.loads(request.content)
        context = json.loads(body["messages"][1]["content"])
        requests.append(context)
        if len(requests) in crash_on:
            raise KeyboardInterrupt("simulate worker death after paid reservation")
        if isinstance(context, dict):
            base = context["feedback"]["evaluated"]
            output = {"candidates": [
                {"name": f"Hypothesis {base + i}", "expression": f"ts_mean(gap, {base + i + 2})",
                 "mechanism": "overnight", "hypothesis": "unverified generator claim"}
                for i in range(context["requested_count"])
            ]}
        else:
            assert all(set(c) == {"id", "expression", "mechanism"} for c in context)
            output = {"reviews": [
                {"id": c["id"], "verdict": "approve", "reason_code": "mock",
                 "explanation": "Mock approval; numerical validation still runs."}
                for c in context
            ]}
        return httpx.Response(200, json={
            "usage": {"total_tokens": 500},
            "choices": [{"message": {"content": json.dumps(output)}}],
        })

    monkeypatch.setattr(
        "loop_research.live.DeepSeekClient",
        lambda *a, **kw: DeepSeekClient(*a, transport=httpx.MockTransport(respond), **kw),
    )
    store = Store(settings.database_path, live_enabled=True)
    run = store.create(RunConfig(
        mode="live", generator="deepseek", rounds=2, batch_size=12, max_candidates=24,
    ))
    store.control(run["id"], "start")
    store.acquire_worker("first")
    return settings, store, run["id"], requests, crash_on


def test_model_batches_resume_review_then_use_development_feedback(model_run):
    settings, store, run_id, requests, _ = model_run
    step(store, "first", settings)  # Persist the first generated batch before restarting.
    store.release_worker("first")
    restored = Store(settings.database_path, live_enabled=True)
    restored.control(run_id, "resume")
    for _ in range(35):
        restored.acquire_worker("second")
        step(restored, "second", settings)
        if restored.get(run_id)["state"] == "completed":
            break
    run = restored.get(run_id)
    assert run["state"] == "completed" and run["cursor"] == 24
    assert run["counts"]["model_calls"] == len(requests) == 4
    assert run["counts"]["tokens"] == 2000
    assert requests[0]["requested_count"] == len(requests[1]) == 12
    assert requests[2]["feedback"]["evaluated"] == 12
    assert sum(requests[2]["feedback"]["outcomes"].values()) == 12
    assert len(requests[2]["feedback"]["recent_attempts"]) == 6
    assert "2016" not in json.dumps(requests[2]["feedback"])
    assert all(c["origin"] == "model" for c in restored.candidates(run_id))
    assert {c["model_batch"] for c in restored.candidates(run_id)} == {1, 2}
    assert {"model_candidates", "model_records", "fsa"}.isdisjoint(run["checkpoint"])
    assert len(restored.get(run_id, internal=True)["checkpoint"]["model_candidates"]) == 12
    assert len(restored.model_records(run_id)) == 4
    with TestClient(create_app(settings)) as client:
        report = client.get(f"/api/v1/runs/{run_id}/report").json()
        assert len(report["model_records"]) == 4
        assert len(report["candidates"]) == 24


def test_crash_in_later_model_batch_retains_reservation_without_resubmission(model_run):
    settings, store, run_id, requests, crash_on = model_run
    crash_on.append(3)
    with pytest.raises(KeyboardInterrupt):
        for _ in range(20):
            store.acquire_worker("first")
            step(store, "first", settings)
    before = PersistentBudget.for_live(settings.budget_path).summary()
    assert before["unresolved_requests"] == 1
    assert store.get(run_id)["cursor"] == 12
    store.release_worker("first")
    restored = Store(settings.database_path, live_enabled=True)
    restored.control(run_id, "resume")
    restored.acquire_worker("second")
    step(restored, "second", settings)
    assert restored.get(run_id)["state"] == "failed"
    assert "未重复请求" in restored.get(run_id)["error"]
    assert len(requests) == 3
    assert PersistentBudget.for_live(settings.budget_path).summary() == before


def test_run_money_limit_blocks_paid_request_before_it_is_sent(model_run):
    settings, store, run_id, requests, _ = model_run
    store.control(run_id, "stop")
    step(store, "first", settings)
    small = store.create(RunConfig(mode="live", generator="deepseek", max_model_cny=0.001))
    store.control(small["id"], "start")
    step(store, "first", settings)
    result = store.get(small["id"])
    assert result["state"] == "budget_exhausted"
    assert result["counts"]["model_calls"] == 0 and not requests


def test_ledger_upgrade_preserves_history_unknown_calls_and_money_cap(tmp_path):
    path = tmp_path / "ledger.db"
    old = PersistentBudget(path, max_cny=40)
    old.carry_floor(59, 119_000)
    old.reserve(1000)  # Old request/token caps are both reached; outcome remains unknown.
    ledger = PersistentBudget.for_live(path)
    ledger.reserve(10_000)
    ledger.settle(10_000, 500)
    summary = ledger.summary()
    assert summary["requests"] == 61 and summary["tokens_charged_or_reserved"] == 120_500
    assert summary["unresolved_requests"] == 1 and summary["hard_cap_cny"] == 40
    assert PersistentBudget.for_live(path).summary() == summary
    ledger.carry_floor(61, 4_999_000)
    ledger.reserve(1000)
    assert ledger.summary()["cost_upper_bound_cny"] == 40
    with pytest.raises(ResearchError, match="预算"):
        ledger.reserve(1)


def test_ledger_upgrade_keeps_custom_limits_and_does_not_repeat(tmp_path):
    path = tmp_path / "custom.db"
    PersistentBudget(path, max_cny=0.008, max_requests=3, max_tokens=2000)
    ledger = PersistentBudget.for_live(path)
    assert ledger.summary()["request_cap"] == 3
    assert ledger.summary()["token_cap"] == 2000
    assert ledger.summary()["hard_cap_cny"] == 0.008
    with pytest.raises(ResearchError):
        ledger.reserve(1001)
    default = tmp_path / "default.db"
    PersistentBudget.for_live(default)
    PersistentBudget(default)  # Explicit later tightening must survive a subsequent reopen.
    assert PersistentBudget.for_live(default).summary()["request_cap"] == 60


def test_candidate_pagination_and_counter_upgrade_preserve_old_results(tmp_path):
    settings = Settings(_env_file=None, state_dir=tmp_path, worker_autostart=False)
    store = Store(settings.database_path)
    run = store.create(RunConfig(rounds=2, batch_size=6))
    store.control(run["id"], "start")
    for _ in range(15):
        store.acquire_worker("test")
        step(store, "test")
    expected = store.get(run["id"])["counts"]
    with store.connection(write=True) as db:
        db.execute("DROP TRIGGER count_candidate")
        db.execute("DROP TABLE run_counts")  # Recreate a database from the previous release.
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/v1/runs/{run['id']}").json()["counts"] == expected
        seen = []
        cursor = 0
        while True:
            page = client.get(
                f"/api/v1/runs/{run['id']}/factors", params={"after": cursor, "limit": 5}
            ).json()
            seen.extend(c["ordinal"] for c in page["items"])
            cursor = page["next_after"]
            if not page["has_more"]:
                break
        assert seen == list(range(1, 13))
        assert client.get(f"/api/v1/runs/{run['id']}/factors?after=12&limit=5").json()["items"] == []
        assert client.get(f"/api/v1/runs/{run['id']}/factors?limit=201").status_code == 422
