"""Copy a reviewed, bounded result bundle into the tiny demo package."""

import argparse
import json
from pathlib import Path

from loop_research.experiments.data import write_json


def export(directory: Path):
    report = json.loads((directory / "report.json").read_text())
    verification = json.loads((directory / "verification.json").read_text())
    if report["status"] != "completed" or verification["status"] != "passed":
        raise ValueError("Only completed and numerically verified experiments can be bundled")
    bundle = {
        k: report[k]
        for k in [
            "id",
            "status",
            "started_at_utc",
            "protocol_sha256",
            "data_commit",
            "data_sha256",
            "asset_count",
            "rows",
            "limitations",
            "seconds",
        ]
    }
    bundle.update(
        model={
            "id": report["config"]["model"],
            "name": report["config"]["model_official_name"],
            "thinking": "disabled",
        },
        seed=report["config"]["seed"],
        periods={k: report["config"][k] for k in ["discovery", "selection", "holdout"]},
        budget=report["budget"],
        verification=verification,
        branches={
            k: {f: v for f, v in summary.items() if f != "rounds"}
            for k, summary in report["branches"].items()
        },
        holdout=report["holdout"],
        cost_one_side=0.001,
        experiment_version=report["config"]["experiment_version"],
        random_seeds=report["config"].get("random_seeds", [report["config"]["seed"]]),
        accepted_factors=[
            {
                **{
                    key: factor[key]
                    for key in (
                        "id",
                        "branch",
                        "expression",
                        "direction",
                        "discovery_ic",
                        "metrics",
                        "accepted",
                    )
                },
                "periods": {
                    key: factor["periods"][key] for key in ("selection", "year2014", "year2015")
                },
                "gates": [
                    {key: gate[key] for key in ("id", "value", "operator", "threshold", "status")}
                    for gate in factor["gates"]
                ],
            }
            for factor in report.get("accepted_factors", [])
        ],
        sources={
            "data": f"https://github.com/yumoxu/stocknet-dataset/tree/{report['data_commit']}/price/raw",
            "pricing": report["budget"]["pricing_source"],
            "model": "https://api-docs.deepseek.com/quick_start/pricing",
        },
    )
    if report["config"]["experiment_version"] == "expanded_search_v2":
        bundle["research_note"] = (
            "在首轮失败诊断后扩展的探索性实验。原 11 项门槛、股票池、交易成本和时间切分保持一致；"
            "先用发现期 IC 筛选，再按开发筛选期夏普排序去相关。各分支共享候选库，"
            "不能作等预算优劣比较。全部入库公式冻结后统一检验留出期，不按测试收益删选。"
        )
    bundle["baselines"] = [
        {
            k: c[k]
            for k in [
                "id",
                "name",
                "expression",
                "direction",
                "discovery_ic",
                "periods",
                "rejection_codes",
                "accepted",
            ]
        }
        for c in json.loads((directory / "E0/candidates.json").read_text())
    ]
    destination = Path("src/loop_research/results")
    encoded = json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False).encode()
    if len(encoded) > 128 * 1024:
        raise ValueError("The demo result bundle must remain below 128 KiB")
    write_json(destination / f"{report['id']}.json", bundle)
    print("bundle:", destination / f"{report['id']}.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    export(parser.parse_args().experiment)
