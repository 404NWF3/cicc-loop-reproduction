from datetime import UTC, datetime

from loop_research.backtest.gates import evaluate_gates
from loop_research.errors import ResearchError
from loop_research.factors.dsl import compile_expression
from loop_research.factors.fsa import FrequentSubtreeAvoidance
from loop_research.factors.generation import propose_fixture
from loop_research.storage import Store


def step(store: Store, token: str, settings=None) -> bool:
    run = store.next_work(token)
    if run is None:
        return False
    if run["config"]["mode"] == "live":
        from loop_research.config import Settings
        from loop_research.live import step_live

        return step_live(store, run, token, settings or Settings())
    config, index = run["config"], run["cursor"]
    if index >= run["target"]:
        store.finish(run["id"], "completed", token, "演示流程完成。市场回测和模型审查均未运行。")
        return True
    elapsed = (datetime.now(UTC) - datetime.fromisoformat(run["started_at"])).total_seconds()
    if index >= config["max_candidates"] or elapsed >= config["max_seconds"]:
        store.finish(run["id"], "budget_exhausted", token, "已到达候选或时间预算，进度已保存。")
        return True
    candidates = store.candidates(run["id"])
    parents = [c for c in candidates if c["status"] == "awaiting_data"]
    proposal = propose_fixture(config["seed"], index, parents)
    candidate = {
        **proposal,
        "id": f"{run['id']}-{index:04d}",
        "run_id": run["id"],
        "ordinal": index + 1,
        "round": index // config["batch_size"] + 1,
        "status": "awaiting_data",
        "reason": "规则检查通过，等待真实数据与完整验证。",
        "fingerprint": None,
        "validation": None,
        "metrics": None,
        "gates": evaluate_gates({}),
        "accepted": False,
    }
    fsa = FrequentSubtreeAvoidance(run["checkpoint"].get("fsa"))
    try:
        node = compile_expression(proposal["expression"])
        candidate["fingerprint"] = node.fingerprint
        candidate["validation"] = {
            "depth": node.depth,
            "nodes": node.size,
            "lookback": node.lookback,
            "canonical": node.canonical(),
            "tree": node.as_dict(),
        }
        duplicate = any(c.get("fingerprint") == node.fingerprint for c in candidates)
        blocked = fsa.inspect(node, candidate["round"]) if config["fsa_enabled"] else []
        if duplicate:
            candidate.update(status="duplicate", reason="规范化表达式与已有候选重复。")
        elif blocked:
            candidate.update(
                status="fsa_blocked",
                reason="表达式命中了暂时冻结的高频骨架。",
                blocked_skeletons=blocked,
            )
        fsa.observe(node)
    except ResearchError as exc:
        candidate.update(status="rejected", reason=exc.message)
    checkpoint = {
        "next_index": index + 1,
        "fsa": fsa.snapshot(),
        "rng": {"seed": config["seed"], "next_index": index + 1},
    }
    store.record_candidate(run, candidate, checkpoint, token)
    return True
