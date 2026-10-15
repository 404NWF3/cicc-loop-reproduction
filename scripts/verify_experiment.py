"""Independent real-data numerical checks; dev-only SciPy, no model calls."""

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import spearmanr

from loop_research.backtest.metrics import forward_returns
from loop_research.experiments.data import load_panel, write_json
from loop_research.factors.dsl import compile_expression, evaluate


def reference_nav(scores, prices, cost=0.001, fraction=0.2):
    """Scalar accounting with an independent root solver and stable symbol tie-breaking."""
    units = dict.fromkeys(prices.columns, 0.0)
    cash, result = 1.0, []
    for position, date in enumerate(prices.index):
        quotes = prices.loc[date].to_dict()
        holdings = {symbol: units[symbol] * quotes[symbol] for symbol in units}
        before = cash + math.fsum(holdings.values())
        if position == len(prices) - 1 or (position >= 1 and (position - 1) % 5 == 0):
            ranked = sorted(
                [symbol for symbol in units if np.isfinite(scores.iloc[position - 1][symbol])],
                key=lambda symbol: (-scores.iloc[position - 1][symbol], symbol),
            )
            chosen = (
                set(ranked[: math.ceil(len(ranked) * fraction)])
                if position < len(prices) - 1
                else set()
            )
            weights = {symbol: (1 / len(chosen) if symbol in chosen else 0.0) for symbol in units}

            def balance(after):
                return (
                    after
                    + cost * math.fsum(abs(after * weights[s] - holdings[s]) for s in units)
                    - before
                )

            after = brentq(balance, 0.0, before, xtol=1e-15)
            fees = cost * math.fsum(abs(after * weights[s] - holdings[s]) for s in units)
            units = {s: after * weights[s] / quotes[s] for s in units}
            cash = before - fees - math.fsum(units[s] * quotes[s] for s in units)
        result.append(cash + math.fsum(units[s] * quotes[s] for s in units))
    return np.asarray(result)


def verify(directory: Path, data: Path, *, persist: bool = True):
    if persist:
        write_json(directory / "verification.json", {"status": "running"})
    report = json.loads((directory / "report.json").read_text())
    panel = load_panel(data)
    labels = forward_returns(panel["open"].loc[:"2013-12-31"])
    max_ic_error, max_nav_error, max_adjustment_error = 0.0, 0.0, 0.0
    baseline = json.loads((directory / "E0/candidates.json").read_text())
    for candidate in baseline:
        values = (
            evaluate(compile_expression(candidate["expression"]), panel) * candidate["direction"]
        )
        observed_ic = pd.read_csv(
            directory / "E0" / candidate["id"] / "discovery_ic.csv", index_col=0
        ).iloc[:, 0]
        observed_ic.index = pd.to_datetime(observed_ic.index)
        for date in observed_ic.dropna().index:
            valid = np.isfinite(values.loc[date]) & np.isfinite(labels.loc[date])
            independent_ic = spearmanr(values.loc[date, valid], labels.loc[date, valid]).statistic
            max_ic_error = max(max_ic_error, abs(independent_ic - observed_ic.loc[date]))
        selected_prices = panel["open"].loc["2014-01-01":]
        independent_nav = reference_nav(values.reindex(selected_prices.index), selected_prices)
        daily = pd.read_csv(directory / "E0" / candidate["id"] / "selection_daily.csv")
        max_nav_error = max(max_nav_error, float(np.max(np.abs(independent_nav - daily.net_nav))))
    frame = pd.read_csv(data / "prices.csv.gz")
    max_adjustment_error = float((frame.close - frame.adj_close).abs().max())
    assert max_ic_error < 1e-10 and max_nav_error < 1e-10 and max_adjustment_error < 1e-10
    gates = Counter()
    for branch in report["branches"]:
        for candidate in json.loads((directory / branch / "candidates.json").read_text()):
            if "gates" in candidate:
                for gate in candidate["gates"]:
                    if gate["status"] == "passed":
                        assert gate["value"] is not None and np.isfinite(gate["value"])
                gates.update(candidate.get("rejection_codes", []))
    calls = [json.loads(p.read_text()) for p in (directory / "calls").glob("*.json")]
    peak_price_estimate = sum(
        (
            c["usage"].get("prompt_cache_hit_tokens", 0) * 0.04
            + c["usage"].get("prompt_cache_miss_tokens", c["usage"]["prompt_tokens"]) * 2
            + c["usage"]["completion_tokens"] * 8
        )
        / 1_000_000
        for c in calls
    )
    result = {
        "status": "passed",
        "baseline_count": len(baseline),
        "ic_reference": "scipy.stats.spearmanr, all six discovery IC series",
        "portfolio_reference": "scalar share accounting + scipy.optimize.brentq, six selection NAVs",
        "max_ic_absolute_error": max_ic_error,
        "max_nav_absolute_error": max_nav_error,
        "adjusted_close_identity_max_error": max_adjustment_error,
        "gate_failures": dict(gates),
        "peak_price_usage_estimate_cny": peak_price_estimate,
        "archived_calls": len(calls),
        "tokens": sum(c["usage"]["total_tokens"] for c in calls),
    }
    assert result["tokens"] == report["budget"]["run_tokens"]
    if persist:
        write_json(directory / "verification.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--data", type=Path, default=Path("data/stocknet-330708b5"))
    args = parser.parse_args()
    verify(args.experiment, args.data)
