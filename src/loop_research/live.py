"""Bounded live research on a packaged, development-only price snapshot.

One worker, one active job, checkpointed model requests, no holdout or online trading.
"""

import asyncio
import json
import random
import re
from datetime import UTC, datetime
from functools import lru_cache
from importlib.resources import files

import numpy as np
import pandas as pd

from loop_research.backtest.gates import evaluate_gates
from loop_research.catalog import MECHANISMS
from loop_research.errors import ResearchError
from loop_research.experiments.data import digest
from loop_research.experiments.evaluation import DevelopmentEvaluator
from loop_research.experiments.expanded import is_degenerate
from loop_research.experiments.runner import BatchReview, bounded_candidate, random_expression
from loop_research.factors.dsl import ARITIES, FIELDS, compile_expression, evaluate
from loop_research.factors.fsa import FrequentSubtreeAvoidance
from loop_research.models.agent import prompt
from loop_research.models.deepseek import DeepSeekClient
from loop_research.models.ledger import PersistentBudget
from loop_research.schemas import CandidateBatch


def manifest():
    return json.loads((files("loop_research.demo") / "manifest.json").read_text())


def budget_for(settings):
    ledger = PersistentBudget(settings.budget_path)
    baseline = json.loads((files("loop_research.demo") / "budget_baseline.json").read_text())
    ledger.carry_floor(baseline["requests"], baseline["tokens"])
    return ledger


@lru_cache(maxsize=1)
def evaluator():
    root = files("loop_research.demo")
    if digest(root / "development.npz") != manifest()["sha256"]:
        raise ResearchError("snapshot_invalid", "历史数据快照校验失败。", 409)
    with np.load(root / "development.npz", allow_pickle=False) as archive:
        dates = pd.to_datetime(archive["dates"], unit="D")
        panel = {
            key: pd.DataFrame(archive[key], index=dates, columns=archive["symbols"])
            for key in ["open", "high", "low", "close", "volume"]
        }
    return DevelopmentEvaluator(panel, None)


def local_proposal(run, records):
    i = run["cursor"]
    seeds = manifest()["seeds"]
    rng = random.Random(run["config"]["seed"] + i * 104729)
    if i < len(seeds):
        seed = seeds[i]
        return {
            "expression": seed["expression"],
            "name": seed["name"],
            "origin": "archive_seed",
            "strategy": "seed",
            "mechanism": "research_seed",
            "hypothesis": "从已归档研究库取出的种子，现场重新计算；不计作全新发现。",
            "llm_review": "not_run",
            "parent_ids": [],
        }
    parents = [c for c in records if c.get("metrics")]
    parents = sorted(
        parents, key=lambda c: (-float(c["periods"]["selection"]["sharpe"] or -999), c["id"])
    )[:12]
    if parents and i % 4 != 3:
        parent = rng.choice(parents)
        expression = parent["expression"]
        if i % 4 == 0:
            expression = f"ts_mean({expression}, {rng.choice([3, 5, 10, 20])})"
        else:
            expression = re.sub(
                r",\s*(1|2|3|5|10|20|40|60)\)",
                lambda _: f", {rng.choice([2, 3, 5, 10, 20, 40, 60])})",
                expression,
            )
        strategy, mechanism, parent_ids = "perturbation", parent["mechanism"], [parent["id"]]
    else:
        expression, mechanism = random_expression(rng)
        strategy, parent_ids = "random", []
    return {
        "expression": expression,
        "name": f"现场候选 {i + 1:03d}",
        "origin": "program",
        "strategy": strategy,
        "mechanism": mechanism,
        "parent_ids": parent_ids,
        "hypothesis": "在开发期检验新的时间尺度或价量关系，方向由发现期 IC 确定。",
        "llm_review": "not_run",
    }


class RunBudget:
    def __init__(self, ledger, run, checkpoint, store, token):
        self.ledger, self.run, self.cp, self.store, self.token = (
            ledger,
            run,
            checkpoint,
            store,
            token,
        )

    def reserve(self, tokens):
        charged = self.cp.get("model_tokens", 0)
        if (charged + tokens) * 8 / 1e6 > self.run["config"]["max_model_cny"]:
            raise ResearchError("model_budget_exhausted", "本次任务模型费用上限已到。", 409)
        self.ledger.reserve(tokens)
        self.cp["model_tokens"] = charged + tokens
        self.cp["model_requests"] = self.cp.get("model_requests", 0) + 1
        self.cp["model_cost_upper_cny"] = self.cp["model_tokens"] * 8 / 1e6
        if not self.store.checkpoint(self.run, self.cp, self.token, "已预留本次模型请求费用。"):
            raise ResearchError("checkpoint_lost", "模型请求未发送：检查点不可写。", 409)

    def settle(self, reserved, actual):
        self.ledger.settle(reserved, actual)
        if type(actual) is int and actual >= 0:
            self.cp["model_tokens"] += actual - reserved
            self.cp["model_cost_upper_cny"] = self.cp["model_tokens"] * 8 / 1e6


def model_stage(store, run, token, settings):
    cp = dict(run["checkpoint"])
    phase = cp.get("model_phase", "new")
    if phase == "ready":
        return False
    if phase in {"generating", "reviewing"}:
        # A previous worker may have received a paid response. Never resubmit invisibly.
        raise ResearchError(
            "model_outcome_unknown", "上次模型请求中断，保留费用预留；未重复请求。", 409
        )
    ledger = budget_for(settings)
    run_budget = RunBudget(ledger, run, cp, store, token)
    records = list(cp.get("model_records", []))

    def archive(record):
        records.append(record)
        cp["model_records"] = records
        store.checkpoint(run, cp, token, "模型响应及用量已保存。")

    client = DeepSeekClient(
        settings.model_copy(update={"deepseek_model": "deepseek-flash"}),
        run_budget,
        thinking_enabled=False,
        recorder=archive,
    )
    if phase == "new":
        cp.update(stage="generating", model_phase="generating")
        if not store.checkpoint(run, cp, token, "DeepSeek 正在提出 6 个价量假设…"):
            return True
        payload = {
            "requested_count": 6,
            "allowed_fields": list(FIELDS),
            "allowed_operators": ARITIES,
            "allowed_mechanisms": MECHANISMS,
            "windows": [2, 3, 5, 10, 20, 40, 60],
            "context": "课堂现场研究，使用历史开发快照；提出低复杂度、可解释的价量因子。"
            "不含任何测试期结果。深度<=6，节点<=32，回看<=120。",
        }

        async def generate():
            if "deepseek-flash" not in await client.list_models():
                raise ResearchError("blocked_model", "官方模型列表中没有目标型号。", 409)
            return await client.generate_json(
                [
                    {"role": "system", "content": prompt("generator")},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                CandidateBatch,
                max_tokens=1600,
                deadline_seconds=60,
            )

        output = asyncio.run(generate())["output"]
        cp["model_candidates"] = [
            {**c, "id": f"M{i}", "origin": "model", "strategy": "mechanism", "parent_ids": []}
            for i, c in enumerate(output["candidates"][:6])
        ]
        cp.update(stage="generated", model_phase="generated")
        store.checkpoint(run, cp, token, "候选已生成；下一步使用独立上下文审查。")
    elif phase == "generated":
        cp.update(stage="reviewing", model_phase="reviewing")
        if not store.checkpoint(run, cp, token, "DeepSeek 正在独立审查逻辑、量纲与时间安全…"):
            return True
        output = asyncio.run(
            client.generate_json(
                [
                    {
                        "role": "system",
                        "content": prompt("reviewer")
                        + '\n批量返回 {"reviews":[{"id":"M0","verdict":"approve|reject|uncertain",'
                        '"reason_code":"code","explanation":"简短理由"}]}，覆盖全部 id。',
                    },
                    {
                        "role": "user",
                        "content": json.dumps(cp["model_candidates"], ensure_ascii=False),
                    },
                ],
                BatchReview,
                max_tokens=1400,
                deadline_seconds=60,
            )
        )["output"]
        verdicts = {v["id"]: v for v in output["reviews"]}
        for c in cp["model_candidates"]:
            c["review"] = verdicts.get(
                c["id"], {"verdict": "uncertain", "explanation": "未返回审查"}
            )
            c["llm_review"] = c["review"]["verdict"]
        cp.update(stage="evaluating", model_phase="ready")
        store.checkpoint(run, cp, token, "审查完成；程序开始按固定门槛逐条验证。")
    return True


def step_live(store, run, token, settings):
    index, config = run["cursor"], run["config"]
    if index >= run["target"]:
        store.finish(run["id"], "completed", token, "本次现场挖掘完成；结果属于历史开发期筛选。")
        return True
    elapsed = (datetime.now(UTC) - datetime.fromisoformat(run["started_at"])).total_seconds()
    if elapsed >= config["max_seconds"]:
        store.finish(run["id"], "budget_exhausted", token, "达到时间上限，已保存结果。")
        return True
    try:
        if config.get("generator") == "deepseek" and model_stage(store, run, token, settings):
            return True
        records = store.candidates(run["id"])
        cp = dict(run["checkpoint"])
        proposals = cp.get("model_candidates", [])
        if index < len(proposals):
            proposal = {**proposals[index]}
        else:
            proposal = local_proposal(run, records)
        row = {
            **proposal,
            "id": f"{run['id']}-{index:04d}",
            "run_id": run["id"],
            "ordinal": index + 1,
            "round": index // config["batch_size"] + 1,
            "status": "gate_rejected",
            "reason": "",
            "fingerprint": None,
            "validation": None,
            "metrics": None,
            "gates": evaluate_gates({}),
            "accepted": False,
            "is_experiment": True,
        }
        fsa = FrequentSubtreeAvoidance(cp.get("fsa"))
        try:
            with bounded_candidate(5):
                node = compile_expression(row["expression"])
                row.update(
                    fingerprint=node.fingerprint,
                    validation={
                        "depth": node.depth,
                        "nodes": node.size,
                        "lookback": node.lookback,
                        "canonical": node.canonical(),
                        "tree": node.as_dict(),
                    },
                )
                blocked = fsa.inspect(node, row["round"]) if config["fsa_enabled"] else []
                fsa.observe(node)
                if any(c.get("fingerprint") == node.fingerprint for c in records):
                    row.update(status="duplicate", reason="该表达式已在本次任务验证。")
                elif row.get("llm_review") in {"reject", "uncertain"}:
                    row.update(status="llm_rejected", reason=row["review"]["explanation"])
                elif blocked:
                    row.update(status="fsa_blocked", reason="高频骨架暂时冻结。")
                else:
                    engine = evaluator()
                    raw = evaluate(node, engine.panel)
                    if is_degenerate(raw, engine.warmup_end):
                        row.update(status="degenerate", reason="截面信号缺少有效差异。")
                    else:
                        library = [
                            (
                                evaluate(compile_expression(c["expression"]), engine.panel)
                                * c["direction"]
                            ).reindex(engine.opens.index)
                            for c in records
                            if c.get("accepted")
                        ]
                        engine.compute(
                            row, node, library, raw_signal=raw, persist=False, include_series=True
                        )
                        row["reason"] = (
                            "通过全部适用门槛，进入本次研究库。"
                            if row["accepted"]
                            else (
                                "未通过 " + "、".join(row["rejection_codes"]) + "；完整指标已保存。"
                            )
                        )
        except (ResearchError, TimeoutError) as exc:
            row.update(status="rejected", reason=str(exc))
        cp.update(
            next_index=index + 1,
            stage="evaluating",
            fsa=fsa.snapshot(),
            snapshot_sha256=manifest()["sha256"],
            protocol="live_development_v1",
        )
        store.record_candidate(run, row, cp, token)
    except ResearchError as exc:
        state = "budget_exhausted" if "budget" in exc.code else "failed"
        store.finish(run["id"], state, token, exc.message)
    return True
