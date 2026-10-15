"""Rebuild the compact development panel from the checksummed local research data.

No downloads, model calls, holdout evaluation or budget-ledger changes.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from loop_research.experiments.data import digest, load_panel, write_json


def build(source: Path, destination: Path):
    panel = load_panel(source, end="2015-12-31")
    original = json.loads((source / "data_manifest.json").read_text())
    report = json.loads(
        Path("src/loop_research/results/stocknet_flash_20261015_v2.json").read_text()
    )
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "development.npz"
    np.savez_compressed(
        target,
        dates=panel["open"].index.to_numpy(dtype="datetime64[D]").astype(np.int64),
        symbols=np.array(panel["open"].columns, dtype="U16"),
        **{name: frame.to_numpy(dtype=np.float64) for name, frame in panel.items()},
    )
    write_json(
        destination / "manifest.json",
        {
            "id": "stocknet-development-v1",
            "source_commit": original["commit"],
            "original_sha256": original["processed_sha256"],
            "sha256": digest(target),
            "assets": len(panel["open"].columns),
            "dates": len(panel["open"]),
            "start": str(panel["open"].index.min().date()),
            "end": str(panel["open"].index.max().date()),
            "holdout_included": False,
            "cost_one_side": 0.001,
            "rebalance": 5,
            "seeds": [
                {
                    "expression": c["expression"],
                    "name": f"归档研究种子 {c['id']}",
                    "source": c["id"],
                }
                for c in report["accepted_factors"][:6]
            ],
        },
    )
    print(json.dumps({"bytes": target.stat().st_size, "sha256": digest(target)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/stocknet-330708b5"))
    parser.add_argument("--output", type=Path, default=Path("src/loop_research/demo"))
    args = parser.parse_args()
    build(args.source, args.output)
