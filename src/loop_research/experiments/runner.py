"""One small, inspectable E0–E3 experiment; no web-triggered paid computation."""

import hashlib
import json
import random
import re
import signal
import time
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from loop_research.catalog import MECHANISMS, SEED_FACTORS, STRATEGIES
from loop_research.config import Settings
from loop_research.errors import ResearchError
from loop_research.experiments.data import (
    STOCKNET_COMMIT,
    digest,
    load_panel,
    prepare_snapshot,
    write_json,
)
from loop_research.experiments.evaluation import DevelopmentEvaluator, evaluate_holdout
from loop_research.factors.dsl import ARITIES, FIELDS, compile_expression
from loop_research.factors.fsa import FrequentSubtreeAvoidance
from loop_research.models.agent import prompt
from loop_research.models.deepseek import DeepSeekClient
from loop_research.models.ledger import PersistentBudget
from loop_research.schemas import CandidateBatch, ReviewResponse


class BatchVerdict(ReviewResponse):
    id: str


class BatchReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviews: list[BatchVerdict] = Field(min_length=1, max_length=10)


def json_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


@contextmanager
def bounded_candidate(seconds: int):
    def timeout(*_):
        raise TimeoutError("Candidate exceeded its preregistered CPU/wall-clock limit")

    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class ModelCalls:
    def __init__(
        self, directory: Path, budget: PersistentBudget, deadline: float, replay: Path | None = None
    ):
        self.directory, self.budget, self.deadline = directory, budget, deadline
        directory.mkdir()
        self.context = {}
        self.archives = {}
        self.count = 0
        self.replay = replay is not None
        if replay:
            for file in sorted((replay / "calls").glob("*.json")):
                record = json.loads(file.read_text())
                self.archives[(record["branch"], record["round"], record["role"])] = record
            self.client = None
        else:
            self.client = DeepSeekClient(
                Settings(deepseek_model="deepseek-flash"),
                budget,
                thinking_enabled=False,
                recorder=self.record,
            )

    def record(self, record):
        self.count += 1
        record = {
            **record,
            **self.context,
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "prompt_sha256": json_hash(record["messages"]),
        }
        write_json(self.directory / f"{self.count:03d}.json", record)

    async def call(
        self, branch: str, round_number: int, role: str, payload: dict, schema: type[BaseModel]
    ) -> dict:
        instructions = (
            prompt("generator")
            if role == "generator"
            else (
                prompt("reviewer") + "\n本次批量审查。逐条返回 "
                '{"reviews":[{"id":"原始候选id","verdict":"approve|reject|uncertain",'
                '"reason_code":"原因码","explanation":"简短理由"}]}。必须覆盖全部输入 id。'
            )
        )
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        self.context = {"branch": branch, "round": round_number, "role": role}
        if self.replay:
            archive = self.archives.get((branch, round_number, role))
            if not archive or archive["prompt_sha256"] != json_hash(messages):
                raise ResearchError("replay_mismatch", "回放提示词与归档记录不一致。", 409)
            self.count += 1
            write_json(self.directory / f"{self.count:03d}.json", archive)
            return schema.model_validate_json(archive["content"]).model_dump()
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ResearchError("experiment_deadline", "实验墙钟预算已用尽。", 409)
        response = await self.client.generate_json(
            messages, schema, max_tokens=2000, deadline_seconds=min(90, remaining)
        )
        return response["output"]


def random_expression(rng: random.Random) -> tuple[str, str]:
    fields = {
        "ret1": "momentum",
        "gap": "overnight",
        "intraday_return": "intraday",
        "intraday_range": "range_change",
        "rel_volume": "relative_volume",
        "upper_shadow": "upper_shadow",
        "lower_shadow": "lower_shadow",
    }

    def term():
        field = rng.choice(list(fields))
        window = rng.choice([2, 3, 5, 10, 20, 40, 60])
        return (
            f"{rng.choice(['ts_mean', 'ts_std', 'ts_rank', 'delta'])}({field}, {window})",
            fields[field],
        )

    expression, mechanism = term()
    choice = rng.randrange(4)
    if choice == 1:
        other, _ = term()
        expression = f"{rng.choice(['sub', 'add', 'mul', 'safe_div'])}({expression}, {other})"
    elif choice == 2:
        expression = f"{rng.choice(['cs_rank', 'cs_zscore', 'neg', 'abs'])}({expression})"
    elif choice == 3:
        field = rng.choice(list(fields))
        expression = f"ts_corr({field}, {rng.choice(list(fields))}, {rng.choice([5, 10, 20, 40])})"
    return expression, mechanism


def local_candidate(strategy: str, rng: random.Random, pool: list[dict]) -> dict:
    parents = sorted(pool, key=lambda x: (-abs(x.get("discovery_ic") or 0), x["expression"]))[:12]
    parent = rng.choice(parents)
    expression, mechanism = parent["expression"], parent["mechanism"]
    lineage = [parent["id"]] if parent.get("id") else []
    if strategy == "random":
        expression, mechanism = random_expression(rng)
        lineage = []
    elif strategy == "mutation":
        if rng.random() < 0.5:
            expression = f"{rng.choice(['neg', 'abs', 'cs_rank', 'cs_zscore'])}({expression})"
        else:
            field = rng.choice(["ret1", "gap", "intraday_return", "intraday_range", "rel_volume"])
            expression = re.sub(
                r"\b(ret1|gap|intraday_return|intraday_range|rel_volume)\b",
                field,
                expression,
                count=1,
            )
    elif strategy == "perturbation":
        expression = re.sub(
            r",\s*(1|2|3|5|10|20|40|60)\)",
            lambda _: f", {rng.choice([2, 3, 5, 10, 20, 40, 60])})",
            expression,
        )
    elif strategy == "crossover":
        other = rng.choice(parents)
        expression = f"sub(cs_rank({expression}), cs_rank({other['expression']}))"
        if other.get("id"):
            lineage.append(other["id"])
    return {
        "name": f"{strategy} candidate",
        "expression": expression,
        "mechanism": mechanism,
        "strategy": strategy,
        "parent_ids": lineage,
        "hypothesis": "本地类型受限价量表达式；经济含义与收益需独立检验。",
        "origin": "program",
        "llm_review": "not_sampled",
    }


def summarize(candidates: list[dict], rounds: list[dict], complete: bool) -> dict:
    numeric = [c for c in candidates if "metrics" in c]
    return {
        "status": "completed" if complete else "partial",
        "attempts": len(candidates),
        "legal": sum("fingerprint" in c for c in candidates),
        "backtested": len(numeric),
        "accepted": sum(c.get("accepted", False) for c in candidates),
        "unique_expressions": len({c["fingerprint"] for c in candidates if "fingerprint" in c}),
        "unique_skeletons": len({c["skeleton"] for c in candidates if "skeleton" in c}),
        "mechanisms": dict(Counter(c["mechanism"] for c in numeric)),
        "strategies": dict(Counter(c["strategy"] for c in candidates)),
        "outcomes": dict(Counter(c["status"] for c in candidates)),
        "gate_failures": dict(Counter(g for c in numeric for g in c["rejection_codes"])),
        "llm_reviews": dict(Counter(c["llm_review"] for c in candidates)),
        "mean_coverage": sum(c["metrics"]["coverage"] for c in numeric) / len(numeric)
        if numeric
        else None,
        "rounds": rounds,
    }


async def run_branch(
    name: str, config: dict, panel: dict, destination: Path, model: ModelCalls, deadline: float
) -> tuple[list, dict]:
    destination.mkdir()
    evaluator = DevelopmentEvaluator(panel, destination)
    rng = random.Random(config["seed"])
    pool = [dict(item) for item in SEED_FACTORS]
    candidates, library, rounds = [], [], []
    seen = set()
    fsa = FrequentSubtreeAvoidance()
    weights = {s["id"]: s["weight"] for s in STRATEGIES}
    desired, used = Counter(), Counter()
    count = (
        6
        if name == "E0"
        else config["random_attempts"]
        if name == "E1"
        else (config["rounds"] * config["batch_size"])
    )
    round_count = 1 if name in {"E0", "E1"} else config["rounds"]
    complete = False
    try:
        for round_number in range(round_count):
            if time.monotonic() >= deadline:
                raise ResearchError("experiment_deadline", "实验时间预算耗尽。", 409)
            size = count if name in {"E0", "E1"} else config["batch_size"]
            strategies = []
            for _ in range(size):
                if name in {"E0", "E1"}:
                    strategy = "baseline" if name == "E0" else "random"
                else:
                    desired.update(weights)
                    strategy = max(weights, key=lambda key: desired[key] - used[key])
                    used[strategy] += 1
                strategies.append(strategy)
            mechanism_count = strategies.count("mechanism")
            generated = []
            if mechanism_count:
                output = await model.call(
                    name,
                    round_number,
                    "generator",
                    {
                        "requested_count": mechanism_count,
                        "parent_expressions": [
                            p["expression"]
                            for p in sorted(pool, key=lambda p: -abs(p.get("discovery_ic") or 0))[
                                :8
                            ]
                        ],
                        "mechanism_coverage": dict(
                            Counter(c["mechanism"] for c in candidates if c.get("metrics"))
                        ),
                        "rejection_codes": dict(Counter(c["status"] for c in candidates[-30:])),
                        "blocked_skeletons": sorted(fsa.blocked)[:30] if name == "E2" else [],
                        "allowed_fields": list(FIELDS),
                        "operators_and_arities": ARITIES,
                        "mechanisms": MECHANISMS,
                        "rolling_windows": [2, 3, 5, 10, 20, 40, 60],
                        "max_depth": 6,
                        "max_nodes": 32,
                        "max_lookback": 120,
                    },
                    CandidateBatch,
                )
                generated = output["candidates"][:mechanism_count]
            batch, nodes = [], {}
            for strategy in strategies:
                number = len(candidates) + len(batch)
                candidate = {
                    "id": f"{name}-{number:03d}",
                    "round": round_number,
                    "accepted": False,
                    "llm_review": "not_sampled",
                }
                if name == "E0":
                    candidate.update(
                        dict(SEED_FACTORS[number]), strategy="baseline", origin="fixed"
                    )
                elif strategy == "mechanism":
                    if not generated:
                        candidate.update(
                            expression="",
                            mechanism="unknown",
                            strategy=strategy,
                            status="generation_missing",
                            origin="deepseek",
                            rejection_codes=["generation_missing"],
                        )
                        batch.append(candidate)
                        continue
                    candidate.update(generated.pop(0), strategy=strategy, origin="deepseek")
                else:
                    candidate.update(local_candidate(strategy, rng, pool))
                try:
                    if candidate["mechanism"] not in MECHANISMS:
                        raise ValueError("Unknown mechanism")
                    node = compile_expression(candidate["expression"])
                    candidate.update(
                        fingerprint=node.fingerprint,
                        skeleton=node.canonical(True),
                        lookback=node.lookback,
                        status="pending",
                    )
                    blocked = fsa.inspect(node, round_number) if name == "E2" else []
                    fsa.observe(node)
                    if node.fingerprint in seen:
                        candidate.update(status="duplicate", rejection_codes=["exact_duplicate"])
                    elif blocked:
                        candidate.update(
                            status="fsa_rejected",
                            rejection_codes=["fsa_blocked"],
                            blocked_skeletons=blocked,
                        )
                    else:
                        nodes[candidate["id"]] = node
                    seen.add(node.fingerprint)
                except (ResearchError, ValueError) as error:
                    candidate.update(
                        status="dsl_rejected",
                        rejection_codes=[
                            error.code if isinstance(error, ResearchError) else "invalid_mechanism"
                        ],
                    )
                batch.append(candidate)
            if name in {"E2", "E3"}:
                review_rng = random.Random(config["seed"] + round_number * 104729)
                sampled = [
                    c
                    for c in batch
                    if c["status"] == "pending"
                    and (c["strategy"] == "mechanism" or review_rng.random() < 0.25)
                ]
                if sampled:
                    payload = {
                        "candidates": [
                            {
                                "id": c["id"],
                                "expression": c["expression"],
                                "mechanism": c["mechanism"],
                            }
                            for c in sampled
                        ],
                        "timing": "daily signal after close; trade next market open",
                        "data_frequency": "adjusted_daily_OHLCV",
                        "field_definitions": {
                            "ret1": "close / prior_close - 1",
                            "gap": "open / prior_close - 1",
                            "intraday_return": "close / open - 1",
                            "intraday_range": "(high-low) / prior_close",
                            "rel_volume": "volume / trailing_20_day_mean_volume",
                        },
                    }
                    output = await model.call(name, round_number, "reviewer", payload, BatchReview)
                    reviews = {r["id"]: r for r in output["reviews"]}
                    if set(reviews) != {c["id"] for c in sampled} or len(reviews) != len(
                        output["reviews"]
                    ):
                        raise ResearchError(
                            "review_id_mismatch", "批量审查返回的候选 ID 不匹配。", 502
                        )
                    for candidate in sampled:
                        review = reviews[candidate["id"]]
                        candidate.update(llm_review=review["verdict"], review=review)
                        if review["verdict"] != "approve":
                            candidate.update(
                                status="llm_rejected", rejection_codes=[review["reason_code"]]
                            )
            for candidate in batch:
                if time.monotonic() >= deadline:
                    raise ResearchError("experiment_deadline", "实验时间预算耗尽。", 409)
                started = time.monotonic()
                if candidate["status"] == "pending":
                    try:
                        with bounded_candidate(config["candidate_timeout_seconds"]):
                            values = evaluator.compute(candidate, nodes[candidate["id"]], library)
                        pool.append(dict(candidate))
                        if candidate["accepted"]:
                            library.append(values)
                    except (ResearchError, TimeoutError) as error:
                        candidate.update(
                            status="numeric_rejected",
                            accepted=False,
                            rejection_codes=[
                                error.code
                                if isinstance(error, ResearchError)
                                else "candidate_timeout"
                            ],
                        )
                candidate["seconds"] = time.monotonic() - started
                candidates.append(candidate)
                write_json(destination / "candidates.json", candidates)
            update = None
            if name in {"E2", "E3"} and (round_number + 1) % 3 == 0:
                recent = candidates[-30:]
                repeated = sum(c["status"] in {"duplicate", "fsa_rejected"} for c in recent) / len(
                    recent
                )
                if repeated > 0.5:
                    weights["random"] += 0.05
                    weights["mechanism"] += 0.05
                    weights["mutation"] -= 0.05
                    weights["crossover"] -= 0.05
                    update = "repetition_over_50pct"
                elif any(c.get("accepted") for c in recent) and repeated < 0.25:
                    weights["mutation"] += 0.025
                    weights["perturbation"] += 0.025
                    weights["random"] -= 0.025
                    weights["crossover"] -= 0.025
                    update = "new_acceptance_low_repetition"
                # Initial sum is one and paired updates preserve it; box-constrained projection.
                for _ in range(20):
                    weights = {k: min(0.4, max(0.05, v)) for k, v in weights.items()}
                    residual = 1 - sum(weights.values())
                    free = [k for k, v in weights.items() if 0.05 < v < 0.4]
                    if abs(residual) < 1e-12 or not free:
                        break
                    for key in free:
                        weights[key] += residual / len(free)
            rounds.append(
                {
                    "round": round_number,
                    "weights_next": dict(weights),
                    "weight_update": update,
                    "fsa": fsa.snapshot(),
                    "outcomes": dict(Counter(c["status"] for c in batch)),
                }
            )
            write_json(destination / "rounds.json", rounds)
            print(
                json.dumps(
                    {
                        "branch": name,
                        "round": round_number + 1,
                        "attempts": len(candidates),
                        "accepted": len(library),
                        "model_calls": model.count,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        complete = len(candidates) == count
    finally:
        summary = summarize(candidates, rounds, complete)
        write_json(destination / "summary.json", summary)
        write_json(destination / "candidates.json", candidates)
    return candidates, summary


def validate_config(config: dict):
    expected = {
        "model": "deepseek-flash",
        "data_commit": STOCKNET_COMMIT,
        "warmup_trading_days": 120,
        "label_horizon": 5,
        "execution_lag": 1,
        "rebalance": 5,
        "top_fraction": 0.2,
        "cost_one_side": 0.001,
        "gate_profile": "demo_joint_v1",
        "branches": ["E0", "E1", "E2", "E3"],
        "max_composite_factors": 5,
        "candidate_timeout_seconds": 5,
        "discovery": ["2012-09-04", "2013-12-31"],
        "selection": ["2014-01-01", "2015-12-31"],
        "holdout": ["2016-01-01", "2017-09-01"],
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError("Configuration changes require a versioned implementation/protocol")
    if not (
        1 <= config["rounds"] <= 10
        and config["batch_size"] == 10
        and 1 <= config["random_attempts"] <= 100
        and 1 <= config["max_seconds"] <= 1800
    ):
        raise ValueError("Experiment is larger than the bounded local protocol")


async def run_experiment(
    config: dict,
    data_dir: Path,
    destination: Path,
    ledger_path: Path,
    *,
    replay: Path | None = None,
) -> dict:
    config = json.loads(json.dumps(config, default=str))
    validate_config(config)
    if destination.exists():
        raise ResearchError("experiment_exists", "实验目录已存在；请显式回放到新目录。", 409)
    manifest = prepare_snapshot(data_dir, max_assets=config["max_assets"])
    destination.mkdir(parents=True)
    write_json(destination / "config.json", config)
    write_json(destination / "data_manifest.json", manifest)
    project = Path(__file__).resolve().parents[3]
    source_files = (
        sorted((project / "src").rglob("*.py"))
        + sorted((project / "src").rglob("*.md"))
        + [project / "pyproject.toml", project / "uv.lock"]
    )
    code_manifest = {str(path.relative_to(project)): digest(path) for path in source_files}
    write_json(destination / "code_manifest.json", code_manifest)
    with zipfile.ZipFile(destination / "source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files:
            archive.write(path, str(path.relative_to(project)))
    budget = PersistentBudget(
        ledger_path,
        max_cny=config["max_cny"],
        max_requests=config["max_requests"],
        max_tokens=config["max_tokens"],
    )
    initial_budget = budget.summary()
    started = time.monotonic()
    deadline = started + config["max_seconds"]
    model = ModelCalls(destination / "calls", budget, deadline, replay)
    report = {
        "id": destination.name,
        "status": "running",
        "config": config,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "protocol_sha256": json_hash(config),
        "data_commit": manifest["commit"],
        "data_sha256": manifest["processed_sha256"],
        "code_sha256": json_hash(code_manifest),
        "asset_count": len(manifest["symbols"]),
        "rows": manifest["rows"],
        "limitations": manifest["limitations"],
        "branches": {},
        "replay_of": replay.name if replay else None,
    }
    write_json(destination / "preregistration.json", report)
    candidates_by_branch = {}
    try:
        if not replay:
            ids = await model.client.list_models()
            if config["model"] not in ids:
                raise ResearchError("blocked_model", "已核实的目标模型不在官方列表中。", 409)
        panel = load_panel(data_dir)
        for branch in config["branches"]:
            candidates, summary = await run_branch(
                branch, config, panel, destination / branch, model, deadline
            )
            report["branches"][branch] = summary
            candidates_by_branch[branch] = candidates
            write_json(destination / "progress.json", report)
        frozen = {
            "experiment_id": destination.name,
            "protocol_sha256": report["protocol_sha256"],
            "data_sha256": manifest["processed_sha256"],
            "branches": {},
            "selection_rule": "selection excess Sharpe descending; fingerprint tie-break; max 5",
            "frozen_at_utc": datetime.now(UTC).isoformat(),
        }
        for branch, candidates in candidates_by_branch.items():
            accepted = sorted(
                [c for c in candidates if c.get("accepted")],
                key=lambda c: (-c["periods"]["selection"]["sharpe"], c["fingerprint"]),
            )[:5]
            frozen["branches"][branch] = [
                {k: c[k] for k in ("id", "expression", "direction", "fingerprint")}
                for c in accepted
            ]
        write_json(destination / "freeze.json", frozen)
        report["freeze_sha256"] = digest(destination / "freeze.json")
        report["holdout"] = evaluate_holdout(
            load_panel(data_dir, end=None), candidates_by_branch, frozen, destination
        )
        write_json(destination / "holdout.json", report["holdout"])
        report["status"] = "completed"
    except (ResearchError, TimeoutError) as error:
        report.update(
            status="partial",
            error={"code": getattr(error, "code", "timeout"), "message": str(error)},
        )
        for branch in config["branches"]:
            file = destination / branch / "summary.json"
            if file.exists():
                report["branches"][branch] = json.loads(file.read_text())
        report["holdout"] = None
    finally:
        end_budget = budget.summary()
        report["budget"] = {
            **end_budget,
            "run_requests": 0 if replay else end_budget["requests"] - initial_budget["requests"],
            "run_tokens": 0
            if replay
            else end_budget["tokens_charged_or_reserved"]
            - initial_budget["tokens_charged_or_reserved"],
            "run_cost_upper_bound_cny": 0
            if replay
            else end_budget["cost_upper_bound_cny"] - initial_budget["cost_upper_bound_cny"],
            "replayed_responses": model.count if replay else 0,
        }
        report["seconds"] = time.monotonic() - started
        write_json(destination / "report.json", report)
    return report
