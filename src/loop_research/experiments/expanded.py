"""Versioned, bounded follow-up search; holdout opens only after the library is frozen.

This is exploratory development after v1, not a new independent test of v1 hypotheses.
No threshold is lowered and every attempted formula (including invalid ones) is retained.
"""

import argparse
import asyncio
import fcntl
import json
import random
import re
import time
import zipfile
from collections import Counter
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

from loop_research.backtest.gates import GATES
from loop_research.backtest.metrics import rank_ic
from loop_research.catalog import MECHANISMS, SEED_FACTORS
from loop_research.errors import ResearchError
from loop_research.experiments.data import digest, load_panel, write_json
from loop_research.experiments.evaluation import DevelopmentEvaluator, evaluate_holdout
from loop_research.experiments.runner import (
    BatchReview,
    ModelCalls,
    bounded_candidate,
    json_hash,
)
from loop_research.factors.dsl import ARITIES, FIELDS, compile_expression, evaluate
from loop_research.models.ledger import PersistentBudget
from loop_research.schemas import CandidateBatch

FIELDS_DIMENSIONLESS = [
    "ret1",
    "gap",
    "intraday_return",
    "intraday_range",
    "rel_volume",
    "upper_shadow",
    "lower_shadow",
]
WINDOWS = [2, 3, 5, 10, 20, 40, 60]
PROTOCOL = {
    "experiment_version": "expanded_search_v2",
    "model": "deepseek-flash",
    "model_official_name": "DeepSeek-V4.1-Flash",
    "thinking": "disabled",
    "seed": 20261015,
    "random_seeds": [17, 43, 101],
    "random_per_seed": 1000,
    "model_batches": 5,
    "model_candidates_per_batch": 8,
    "adaptive_rounds": 3,
    "adaptive_per_round": 800,
    "parent_limit": 30,
    "max_attempts": 8000,
    "max_seconds": 1800,
    "candidate_timeout_seconds": 5,
    "max_cny": 40,
    "max_requests": 60,
    "max_tokens": 120000,
    "discovery": ["2012-09-04", "2013-12-31"],
    "selection": ["2014-01-01", "2015-12-31"],
    "holdout": ["2016-01-01", "2017-09-01"],
    "warmup_trading_days": 120,
    "label_horizon": 5,
    "execution_lag": 1,
    "rebalance": 5,
    "top_fraction": 0.2,
    "cost_one_side": 0.001,
    "gate_profile": "demo_joint_v1",
    "gates": GATES,
    "branches": ["E0", "E4", "E5", "E6", "E7"],
    "discovery_prefilter": "abs(mean Rank IC) > .03, >=120 valid days; no selection backtest otherwise",
    "degeneracy_filter": "at least 90% of post-warmup rows have relative cross-sectional spread > 1e-10",
    "parent_selection": "selection excess Sharpe descending, fingerprint tie-break; IC-qualified only",
    "library_selection": "all non-correlation gates first; greedy selection Sharpe order, abs rank correlation < .7",
    "max_composite_factors": 5,
    "stop_rule": "finish all fixed batches even after an acceptance; 8000 attempts / 1800s hard stop",
    "interpretation": "exploratory follow-up using the same development data; no FSA causal comparison",
    "holdout_rule": "evaluate entire frozen library once; no holdout-based removal or retuning",
}


def candidate(expression, branch, *, mechanism="mixed", **extra):
    return {
        "expression": expression,
        "branch": branch,
        "name": f"{branch} hypothesis",
        "mechanism": mechanism,
        "strategy": branch,
        "parent_ids": [],
        "hypothesis": "Price/volume persistence or interaction; empirical hypothesis only.",
        "origin": "program",
        "llm_review": "not_sampled",
        **extra,
    }


def atoms():
    result = [
        f"{op}({field}, {w})"
        for field in FIELDS_DIMENSIONLESS
        for op in ["ts_mean", "ts_std", "ts_rank", "delta"]
        for w in WINDOWS
    ]
    for w in WINDOWS:
        result.extend(
            [
                f"sub(safe_div(close, delay(close, {w})), 1)",
                f"safe_div(ts_mean(ret1, {w}), ts_std(ret1, {w}))",
                f"safe_div(sub(close, ts_min(low, {w})), sub(ts_max(high, {w}), ts_min(low, {w})))",
            ]
        )
    return result


def initial_plan():
    plan = [
        candidate(s["expression"], "E0", name=s["name"], mechanism=s["mechanism"])
        for s in SEED_FACTORS
    ]
    base = atoms()
    for expression in base:
        for smoothing in [None, 5, 20]:
            e = expression if smoothing is None else f"ts_mean({expression}, {smoothing})"
            plan.append(candidate(e, "E4", mechanism="systematic_price_volume"))
    for left, right in combinations(FIELDS_DIMENSIONLESS, 2):
        for w in [5, 10, 20, 40, 60]:
            for smoothing in [None, 5, 20]:
                e = f"ts_corr({left}, {right}, {w})"
                if smoothing:
                    e = f"ts_mean({e}, {smoothing})"
                plan.append(candidate(e, "E4", mechanism="smoothed_correlation"))
    for seed in PROTOCOL["random_seeds"]:
        rng = random.Random(seed)
        for _ in range(PROTOCOL["random_per_seed"]):
            left, right = rng.sample(base, 2)
            op = rng.choice(["add", "sub", "mul"])
            transform = rng.choice(["cs_rank", "cs_zscore"])
            e = f"{op}({transform}({left}), {transform}({right}))"
            plan.append(candidate(e, "E5", seed=seed, mechanism="rank_interaction"))
    return plan


def variants(expression):
    yield expression
    for w in [3, 5, 10, 20]:
        yield f"ts_mean({expression}, {w})"
    for w in [5, 10, 20, 40, 60]:
        yield re.sub(r",\s*(1|2|3|5|10|20|40|60)\)", f", {w})", expression, count=1)


def adaptive_plan(records, round_number):
    parents = sorted(
        [
            r
            for r in records
            if r.get("periods")
            and r["metrics"]["abs_ic"] > 0.03
            and r["periods"]["selection"]["sharpe"] is not None
        ],
        key=lambda r: (-r["periods"]["selection"]["sharpe"], r["fingerprint"]),
    )[: PROTOCOL["parent_limit"]]
    rng = random.Random(PROTOCOL["seed"] + round_number)
    result = []
    for _ in range(PROTOCOL["adaptive_per_round"]):
        if not parents:
            result.append(candidate(rng.choice(atoms()), "E7", round=round_number))
            continue
        left, right = rng.choice(parents), rng.choice(parents)
        e, parent_ids = left["expression"], [left["id"]]
        mode = rng.randrange(4)
        if mode == 0:
            e = re.sub(r",\s*(1|2|3|5|10|20|40|60)\)", lambda _: f", {rng.choice(WINDOWS)})", e)
        elif mode == 1:
            e = f"ts_mean({e}, {rng.choice([3, 5, 10, 20])})"
        else:
            # The directions used in blends were learned from discovery, never holdout.
            a = e if left["direction"] == 1 else f"neg({e})"
            b = right["expression"] if right["direction"] == 1 else f"neg({right['expression']})"
            e = f"{rng.choice(['add', 'sub'])}(cs_rank({a}), cs_rank({b}))"
            parent_ids.append(right["id"])
        result.append(
            candidate(
                e, "E7", parent_ids=parent_ids, round=round_number, mechanism="adaptive_development"
            )
        )
    return result


def is_degenerate(signal, warmup_end):
    values = signal.loc[warmup_end:]
    spread = values.max(axis=1) - values.min(axis=1)
    scale = values.abs().max(axis=1).clip(lower=1)
    return float((spread > 1e-10 * scale).mean()) < 0.9


def summaries(records):
    result = {}
    for branch in PROTOCOL["branches"]:
        rows = [r for r in records if r["branch"] == branch]
        numeric = [r for r in rows if "periods" in r]
        result[branch] = {
            "status": "completed",
            "attempts": len(rows),
            "legal": sum("fingerprint" in r for r in rows),
            "backtested": len(numeric),
            "accepted": sum(r.get("accepted", False) for r in rows),
            "quality_passed": sum(r.get("quality_passed", False) for r in rows),
            "unique_expressions": len({r["fingerprint"] for r in rows if "fingerprint" in r}),
            "unique_skeletons": len({r["skeleton"] for r in rows if "skeleton" in r}),
            "outcomes": dict(Counter(r["status"] for r in rows)),
            "gate_failures": dict(Counter(g for r in rows for g in r.get("rejection_codes", []))),
        }
    return result


async def model_plan(model, destination):
    result, errors = [], []
    themes = [
        "Slow volume/range co-movement; 20-60 day horizons; smooth unstable correlations.",
        "Risk-normalized trend persistence, separating overnight and intraday effects.",
        "Relative volume conditional on price position and candle shadows.",
        "Combine two distinct signals with compatible dimensions; avoid noisy daily ranks.",
        "Novel low-turnover price-volume hypotheses using rolling extrema and dispersion.",
    ]
    for i, theme in enumerate(themes):
        try:
            generated = await model.call(
                "E6",
                i,
                "generator",
                {
                    "requested_count": PROTOCOL["model_candidates_per_batch"],
                    "theme": theme,
                    "allowed_fields": list(FIELDS),
                    "allowed_operators": ARITIES,
                    "allowed_mechanisms": MECHANISMS,
                    "windows": WINDOWS,
                    "constraints": "depth<=6, nodes<=32, lookback<=120. No self-correlation."
                    " Keep formulas shallow so 5/20-day smoothing is valid."
                    " Development-only exploratory expansion. No claimed performance.",
                    "prior_diagnosis": "v1: 217 candidates failed Calmar>1 after 0.1% one-side costs;"
                    " mostly short/noisy and redundant hypotheses. No holdout observations supplied.",
                },
                CandidateBatch,
            )
            batch = [
                candidate(
                    c["expression"],
                    "E6",
                    **{k: v for k, v in c.items() if k != "expression"},
                    origin="model",
                    model_id=f"M{i}-{j}",
                )
                for j, c in enumerate(generated["candidates"][:8])
            ]
            review = await model.call(
                "E6",
                i,
                "reviewer",
                {
                    "candidates": [
                        {
                            "id": c["model_id"],
                            "expression": c["expression"],
                            "hypothesis": c["hypothesis"],
                        }
                        for c in batch
                    ],
                    "instruction": "Review causal plausibility, dimensions and temporal safety."
                    " Do not infer or require empirical profitability. No performance data supplied.",
                },
                BatchReview,
            )
            verdicts = {r["id"]: r for r in review["reviews"]}
            for c in batch:
                verdict = verdicts.get(c["model_id"], {"verdict": "uncertain"})
                c["llm_review"] = verdict["verdict"]
                c["review"] = verdict
                if verdict["verdict"] != "approve":
                    result.append({**c, "pre_rejected": "llm_rejected"})
                else:
                    for j, e in enumerate(variants(c["expression"])):
                        result.append(
                            {
                                **c,
                                "expression": e,
                                "variant": j,
                                "origin": "model" if j == 0 else "model_local_variant",
                                "llm_review": "approve" if j == 0 else "parent_approved",
                            }
                        )
        except ResearchError as exc:
            errors.append({"batch": i, "code": exc.code, "message": str(exc)})
            # Do not replace paid failures with extra generations or retry unknown outcomes.
            break
    write_json(destination / "model_plan.json", {"candidates": result, "errors": errors})
    return result, errors


async def run(destination, data, ledger, replay=None):
    if destination.exists():
        raise ValueError("Experiment output must be a new directory")
    destination.mkdir(parents=True)
    started = time.monotonic()
    deadline = started + PROTOCOL["max_seconds"]
    budget = PersistentBudget(ledger)
    before = budget.summary()
    manifest = json.loads((data / "data_manifest.json").read_text())
    report = {
        "id": destination.name,
        "status": "running",
        "config": PROTOCOL,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "protocol_sha256": json_hash(PROTOCOL),
        "data_commit": manifest["commit"],
        "data_sha256": manifest["processed_sha256"],
        "asset_count": len(manifest["symbols"]),
        "rows": manifest["rows"],
        "limitations": manifest["limitations"]
        + [
            "Exploratory expansion after seeing v1 development failures; many hypotheses tested.",
            "Branches share a library and E7 uses development feedback; no controlled FSA comparison.",
        ],
        "replay_of": replay.name if replay else None,
    }
    project = Path(__file__).resolve().parents[3]
    sources = sorted((project / "src").rglob("*.py")) + sorted((project / "src").rglob("*.md"))
    sources += [project / "pyproject.toml", project / "uv.lock"]
    code = {str(p.relative_to(project)): digest(p) for p in sources}
    report["code_sha256"] = json_hash(code)
    write_json(destination / "code_manifest.json", code)
    with zipfile.ZipFile(destination / "source_snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for p in sources:
            archive.write(p, str(p.relative_to(project)))
    write_json(destination / "preregistration.json", report)
    write_json(destination / "config.json", PROTOCOL)
    write_json(destination / "data_manifest.json", manifest)
    plan = initial_plan()
    write_json(destination / "initial_plan.json", plan)
    model = ModelCalls(destination / "calls", budget, deadline, replay)
    if not replay and PROTOCOL["model"] not in await model.client.list_models():
        raise ValueError("Verified official model is unavailable")
    proposals, model_errors = await model_plan(model, destination)
    plan += proposals
    panel = load_panel(data)
    evaluators = {}
    for branch in PROTOCOL["branches"]:
        folder = destination / branch
        folder.mkdir()
        evaluators[branch] = DevelopmentEvaluator(panel, folder)
    records, seen = [], {}
    counters = Counter()

    def screen(batch):
        for row in batch:
            if len(records) >= PROTOCOL["max_attempts"] or time.monotonic() > deadline:
                raise TimeoutError("Preregistered search limit reached")
            branch = row["branch"]
            counters[branch] += 1
            row.update(id=f"{branch}-{counters[branch]:05d}", accepted=False)
            evaluator = evaluators[branch]
            try:
                with bounded_candidate(PROTOCOL["candidate_timeout_seconds"]):
                    if row.get("pre_rejected"):
                        row["status"] = row["pre_rejected"]
                    else:
                        node = compile_expression(row["expression"])
                        row.update(fingerprint=node.fingerprint, skeleton=node.canonical(True))
                        if node.fingerprint in seen:
                            row.update(status="duplicate", duplicate_of=seen[node.fingerprint])
                        else:
                            seen[node.fingerprint] = row["id"]
                            raw = evaluate(node, panel)
                            if is_degenerate(raw, evaluator.warmup_end):
                                row["status"] = "degenerate"
                            else:
                                ic = rank_ic(raw.loc[:"2013-12-31"], evaluator.labels).loc[
                                    evaluator.warmup_end :
                                ]
                                mean = float(ic.mean()) if ic.notna().any() else None
                                row.update(discovery_raw_ic=mean, ic_days=int(ic.notna().sum()))
                                if branch != "E0" and (
                                    mean is None or abs(mean) <= 0.03 or row["ic_days"] < 120
                                ):
                                    row.update(
                                        status="discovery_rejected",
                                        rejection_codes=["G01"]
                                        if mean is None or abs(mean) <= 0.03
                                        else ["G11"],
                                    )
                                else:
                                    evaluator.compute(
                                        row,
                                        node,
                                        [],
                                        raw_signal=raw,
                                        raw_ic=ic,
                                        persist=branch == "E0",
                                    )
                                    row["quality_passed"] = row["accepted"]
                                    row["accepted"] = False  # global correlation screen follows
                                    if row["quality_passed"]:
                                        row["status"] = "awaiting_correlation"
            except (ResearchError, TimeoutError) as exc:
                row.update(
                    status="dsl_rejected" if isinstance(exc, ResearchError) else "timeout",
                    error=str(exc),
                )
            records.append(row)
            if len(records) % 100 == 0:
                progress = {
                    "attempts": len(records),
                    "backtested": sum("periods" in r for r in records),
                    "quality_passed": sum(r.get("quality_passed", False) for r in records),
                    "seconds": round(time.monotonic() - started, 1),
                }
                write_json(destination / "progress.json", progress)
                print(json.dumps(progress), flush=True)

    try:
        screen(plan)
        for number in range(PROTOCOL["adaptive_rounds"]):
            batch = adaptive_plan(records, number)
            write_json(destination / f"adaptive_plan_{number}.json", batch)
            screen(batch)
        quality = sorted(
            [r for r in records if r.get("quality_passed")],
            key=lambda r: (-r["periods"]["selection"]["sharpe"], r["fingerprint"]),
        )
        library, accepted = [], []
        for row in quality:
            selected = evaluators[row["branch"]].compute(
                row, compile_expression(row["expression"]), library
            )
            if row["accepted"]:
                library.append(selected)
                accepted.append(row)
        frozen = {
            "experiment_id": destination.name,
            "protocol_sha256": report["protocol_sha256"],
            "data_sha256": report["data_sha256"],
            "frozen_at_utc": datetime.now(UTC).isoformat(),
            "selection_rule": PROTOCOL["library_selection"],
            "branches": {
                "LIBRARY": [
                    {k: r[k] for k in ("id", "expression", "direction", "fingerprint")}
                    for r in accepted
                ]
            },
        }
        write_json(destination / "freeze.json", frozen)
        report["freeze_sha256"] = digest(destination / "freeze.json")
        # Only this point loads post-2015 prices. All accepted factors remain in the report.
        full = load_panel(data, end=None)
        holdout = evaluate_holdout(full, {}, frozen, destination)
        # The library can contain >5 factors; only the prespecified top5 form the main composite.
        top5 = {**frozen, "branches": {"TOP5": frozen["branches"]["LIBRARY"][:5]}}
        holdout.update(evaluate_holdout(full, {}, top5, destination))
        report.update(
            status="completed",
            holdout=holdout,
            accepted_factors=[
                {
                    k: r[k]
                    for k in (
                        "id",
                        "branch",
                        "expression",
                        "direction",
                        "discovery_ic",
                        "periods",
                        "metrics",
                        "gates",
                        "accepted",
                    )
                }
                for r in accepted
            ],
        )
        write_json(destination / "holdout.json", holdout)
    except (ResearchError, TimeoutError) as exc:
        report.update(status="partial", error=str(exc), holdout=None)
    finally:
        report["branches"] = summaries(records)
        for branch in PROTOCOL["branches"]:
            write_json(
                destination / branch / "candidates.json",
                [r for r in records if r["branch"] == branch],
            )
            write_json(destination / branch / "summary.json", report["branches"][branch])
        after = budget.summary()
        report["budget"] = {
            **after,
            "run_requests": 0 if replay else after["requests"] - before["requests"],
            "run_tokens": 0
            if replay
            else after["tokens_charged_or_reserved"] - before["tokens_charged_or_reserved"],
            "run_cost_upper_bound_cny": 0
            if replay
            else after["cost_upper_bound_cny"] - before["cost_upper_bound_cny"],
            "replayed_responses": model.count if replay else 0,
        }
        report.update(seconds=time.monotonic() - started, model_errors=model_errors)
        write_json(destination / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True)
    parser.add_argument("--data", type=Path, default=Path("data/stocknet-330708b5"))
    parser.add_argument("--ledger", type=Path, default=Path("artifacts/budgets/deepseek.sqlite3"))
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", args.id):
        parser.error("Experiment id must be a safe directory name")
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = asyncio.run(run(Path("artifacts") / args.id, args.data, args.ledger, args.replay))
    print(
        json.dumps(
            {
                "id": result["id"],
                "status": result["status"],
                "budget": result["budget"],
                "branches": result["branches"],
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if result["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
