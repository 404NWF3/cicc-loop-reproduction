import pytest

from loop_research.errors import ResearchError
from loop_research.loop.runner import step
from loop_research.schemas import RunConfig
from loop_research.storage import Store


def drain(store, token, maximum=100):
    for _ in range(maximum):
        store.acquire_worker(token)
        if not step(store, token):
            break


def test_pause_resume_and_checkpoint_survive_a_new_worker(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    config = RunConfig(rounds=2, batch_size=5)
    run = store.create(config)
    store.control(run["id"], "start")
    assert store.acquire_worker("first")
    assert not store.acquire_worker("second")
    step(store, "first")
    step(store, "first")
    store.control(run["id"], "pause")
    step(store, "first")
    assert store.get(run["id"])["state"] == "paused"
    assert store.get(run["id"])["cursor"] == 2
    store.release_worker("first")
    restored = Store(tmp_path / "db.sqlite")
    restored.control(run["id"], "resume")
    restored.acquire_worker("second")
    drain(restored, "second")
    final = restored.get(run["id"])
    assert final["state"] == "completed" and final["cursor"] == 10
    candidates = restored.candidates(run["id"])
    assert len({c["id"] for c in candidates}) == 10
    assert [c["ordinal"] for c in candidates] == list(range(1, 11))
    assert all(c["metrics"] is None and not c["accepted"] for c in candidates)
    events = restored.events(run["id"])
    assert restored.events(run["id"], after=events[2]["id"]) == events[3:]


def test_fixture_is_deterministic_across_interruption(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    config = RunConfig(rounds=2, batch_size=8)
    first = store.create(config)
    store.control(first["id"], "start")
    store.acquire_worker("worker-a")
    step(store, "worker-a")
    store.release_worker("worker-a")
    assert store.get(first["id"])["state"] == "interrupted"
    store.control(first["id"], "resume")
    drain(store, "worker-b")
    second = store.create(config)
    store.control(second["id"], "start")
    drain(store, "worker-b")
    a = [(c["expression"], c["status"]) for c in store.candidates(first["id"])]
    b = [(c["expression"], c["status"]) for c in store.candidates(second["id"])]
    assert a == b and len(a) == 16


def test_budget_single_worker_and_idempotent_creation(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    config = RunConfig(rounds=3, batch_size=3, max_candidates=2)
    first = store.create(config, "same-key")
    assert store.create(config, "same-key")["id"] == first["id"]
    with pytest.raises(ResearchError, match="不同配置"):
        store.create(RunConfig(name="different"), "same-key")
    second = store.create(config)
    store.control(first["id"], "start")
    with pytest.raises(ResearchError, match="已有任务"):
        store.control(second["id"], "start")
    drain(store, "worker")
    result = store.get(first["id"])
    assert result["state"] == "budget_exhausted" and result["cursor"] == 2
    assert result["counts"]["model_calls"] == 0
    store.control(second["id"], "start")
    store.control(second["id"], "stop")
    assert store.get(second["id"])["state"] == "stopped"


def test_live_task_never_falls_back_to_fixture(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    run = store.create(RunConfig(mode="live"))
    with pytest.raises(ResearchError, match="未启用现场挖掘"):
        store.control(run["id"], "start")
    assert store.get(run["id"])["state"] == "draft"


def test_storage_quota_stops_new_writes_without_removing_history(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    run = store.create(RunConfig(rounds=1, batch_size=3), "quota-key")
    store.control(run["id"], "start")
    store.acquire_worker("quota-worker")
    store.max_state_bytes = 1
    step(store, "quota-worker")
    assert store.get(run["id"])["state"] == "budget_exhausted"
    assert store.get(run["id"])["cursor"] == 0
    # Existing idempotent requests and reads remain available.
    assert store.create(RunConfig(rounds=1, batch_size=3), "quota-key")["id"] == run["id"]
    with pytest.raises(ResearchError, match="存储预算"):
        store.create(RunConfig())
