"""Small, commit-pinned StockNet price snapshot with discovery-only selection."""

import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from loop_research.data.validation import validate_frame
from loop_research.errors import ResearchError

STOCKNET_COMMIT = "330708b5ddc359961078bef469f43f48992fd6e4"
SOURCE = "https://raw.githubusercontent.com/yumoxu/stocknet-dataset"
DISCOVERY_END = "2013-12-31"
SELECTION_END = "2015-12-31"


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(raw: bytes, symbol: str) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(raw)).rename(columns=lambda x: x.lower().replace(" ", "_"))
    frame["date"] = pd.to_datetime(frame["date"])
    frame["symbol"] = symbol
    frame["raw_close"] = frame["close"]
    frame["adjustment_factor"] = frame["adj_close"] / frame["close"]
    for column in ("open", "high", "low", "close"):
        frame[column] *= frame["adjustment_factor"]
    return frame.sort_values("date")


def prepare_snapshot(destination: Path, *, max_assets: int = 50) -> dict:
    if not 30 <= max_assets <= 50:
        raise ValueError("The preregistered experiment requires 30–50 assets")
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "data_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if digest(destination / "prices.csv.gz") != manifest["processed_sha256"]:
            raise ResearchError("data_checksum", "处理后数据校验和发生变化。", 409)
        if manifest["max_assets"] != max_assets:
            raise ResearchError("data_config_changed", "请为不同股票数创建新的快照目录。", 409)
        return manifest
    tree_url = (
        "https://api.github.com/repos/yumoxu/stocknet-dataset/git/trees/"
        f"{STOCKNET_COMMIT}?recursive=1"
    )
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(tree_url)
        response.raise_for_status()
        paths = sorted(
            item["path"]
            for item in response.json()["tree"]
            if item["path"].startswith("price/raw/") and item["path"].endswith(".csv")
        )
    if len(paths) != 88:
        raise ResearchError("unexpected_universe", "固定版本的源股票数发生变化。", 409)

    def fetch(path):
        symbol = Path(path).stem
        target = destination / "raw" / f"{symbol}.csv"
        target.parent.mkdir(exist_ok=True)
        url = f"{SOURCE}/{STOCKNET_COMMIT}/{path}"
        if not target.exists():
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                if len(response.content) > 500_000:
                    raise ValueError("Unexpectedly large price CSV")
                target.write_bytes(response.content)
        return (
            symbol,
            normalize(target.read_bytes(), symbol),
            {
                "symbol": symbol,
                "url": url,
                "sha256": digest(target),
                "bytes": target.stat().st_size,
            },
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        sources = list(executor.map(fetch, paths))
    frames = {symbol: frame for symbol, frame, _ in sources}
    calendar = frames["AAPL"]["date"]
    discovery_calendar = calendar[calendar <= DISCOVERY_END]
    selection, checks = [], []
    for symbol, frame, _ in sources:
        discovery = frame[frame.date <= DISCOVERY_END]
        coverage = float(discovery.date.isin(discovery_calendar).sum() / len(discovery_calendar))
        quality = validate_frame(discovery)
        eligible = coverage >= 0.9 and quality["valid"] and len(discovery) >= 120
        if eligible and len(selection) < max_assets:
            selection.append(symbol)
        checks.append(
            {
                "symbol": symbol,
                "discovery_coverage": coverage,
                "eligible": eligible,
                "discovery_issues": quality["issues"],
            }
        )
    if len(selection) < 30:
        write_json(destination / "universe_quality.json", checks)
        raise ResearchError("insufficient_assets", "搜索期合格股票不足 30 只。", 409)
    combined = pd.concat([frames[s] for s in selection], ignore_index=True)
    quality = validate_frame(combined)
    # A data error stops the experiment. Never use selection/holdout quality to repick the universe.
    if not quality["valid"]:
        write_json(destination / "quality_failure.json", quality)
        raise ResearchError("invalid_snapshot", "冻结股票池后发现数据错误，实验已停止。", 409)
    missing, outliers = {}, {}
    for symbol in selection:
        frame = frames[symbol].set_index("date").reindex(pd.DatetimeIndex(calendar))
        missing[symbol] = int(frame.close.isna().sum())
        jumps = frame.close.pct_change(fill_method=None).abs() > 0.5
        outliers[symbol] = [str(x.date()) for x in frame.index[jumps]]
    combined = combined.sort_values(["date", "symbol"])
    combined.to_csv(destination / "prices.csv.gz", index=False, compression="gzip")
    manifest = {
        "source": "StockNet/Yahoo Finance historical snapshot",
        "commit": STOCKNET_COMMIT,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "source_files": [source for _, _, source in sources],
        "max_assets": max_assets,
        "symbols": selection,
        "rows": len(combined),
        "trading_days": len(calendar),
        "start": str(calendar.min().date()),
        "end": str(calendar.max().date()),
        "universe_rule": "discovery coverage >=90%, valid OHLCV, >=120 rows; ticker sort; first 50",
        "universe_selection_end": DISCOVERY_END,
        "processing_version": "stocknet_adjusted_ohlc_v1",
        "adjustment": "OHLC * (Adj Close / Close); volume unchanged; no imputation",
        "processed_sha256": digest(destination / "prices.csv.gz"),
        "quality": {
            **quality,
            "missing_calendar_rows": missing,
            "adjusted_close_jumps_over_50pct": outliers,
        },
        "universe_quality": checks,
        "license_url": f"https://github.com/yumoxu/stocknet-dataset/blob/{STOCKNET_COMMIT}/LICENSE",
        "limitations": [
            "Source universe has survivorship/selection bias",
            "Retrospective Yahoo adjustment factors; not point-in-time corporate actions",
            "US equities, not the original A-share universe",
            "LLM pretraining may include the historical period",
            "Overlapping 5-day labels; no IID significance claims",
        ],
    }
    write_json(manifest_path, manifest)
    return manifest


def load_panel(directory: Path, *, end: str | None = SELECTION_END) -> dict[str, pd.DataFrame]:
    manifest = json.loads((directory / "data_manifest.json").read_text())
    if digest(directory / "prices.csv.gz") != manifest["processed_sha256"]:
        raise ResearchError("data_checksum", "数据校验和与冻结记录不一致。", 409)
    frame = pd.read_csv(directory / "prices.csv.gz", parse_dates=["date"])
    if end is not None:
        frame = frame[frame.date <= end]
    calendar = frame[frame.symbol == "AAPL"].date.sort_values()
    frame = frame.set_index(["date", "symbol"])
    return {
        field: frame[field]
        .unstack("symbol")
        .reindex(index=pd.DatetimeIndex(calendar, name="date"), columns=manifest["symbols"])
        .astype(np.float64)
        for field in ("open", "high", "low", "close", "volume")
    }
