"""Independent numerical audit of all admitted factors, including the frozen holdout."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from verify_experiment import reference_nav, verify

from loop_research.backtest.gates import evaluate_gates
from loop_research.experiments.data import digest, load_panel, write_json
from loop_research.factors.dsl import compile_expression, evaluate


def metrics(nav, bench):
    relative = np.asarray(nav) / np.asarray(bench)
    relative /= relative[0]
    returns = relative[1:] / relative[:-1] - 1
    annual = float(relative[-1] ** (252 / len(returns)) - 1)
    std = float(np.std(returns, ddof=1))
    drawdown = float(np.min(relative / np.maximum.accumulate(relative) - 1))
    return {
        "annual_excess": annual,
        "sharpe": float(np.mean(returns) / std * math.sqrt(252)) if std > 1e-12 else None,
        "max_drawdown": drawdown,
        "calmar": annual / abs(drawdown) if drawdown < -1e-12 else None,
    }


def verify_expanded(directory, data):
    # Preserve the six baseline checks as well as checking every successful new candidate.
    # An interrupted/failed expanded audit must never expose a baseline-only "passed" result.
    write_json(directory / "verification.json", {"status": "running"})
    result = verify(directory, data, persist=False)
    report = json.loads((directory / "report.json").read_text())
    frozen = json.loads((directory / "freeze.json").read_text())
    assert report["status"] == "completed"
    assert digest(directory / "freeze.json") == report["freeze_sha256"]
    assert frozen["branches"]["LIBRARY"] == [
        {key: item[key] for key in ("id", "expression", "direction", "fingerprint")}
        for item in (
            json.loads((directory / row["branch"] / row["id"] / "result.json").read_text())
            for row in report["accepted_factors"]
        )
    ]
    panel = load_panel(data, end=None)
    selection = panel["open"].loc["2014-01-01":"2015-12-31"]
    holdout = panel["open"].loc["2016-01-01":]
    discovery = panel["open"].loc[:"2013-12-31"]
    # Explicit forward labels, separately from the implementation's shift operation.
    labels = np.full(discovery.shape, np.nan)
    prices = discovery.to_numpy()
    labels[:-6] = prices[6:] / prices[1:-5] - 1
    labels = pd.DataFrame(labels, index=discovery.index, columns=discovery.columns)
    benchmark = reference_nav(selection * 0 + 1, selection, fraction=1)
    holdout_benchmark = reference_nav(holdout * 0 + 1, holdout, fraction=1)
    max_ic, max_nav, max_metric, max_corr = 0.0, 0.0, 0.0, 0.0
    prior = []
    selection_blends, holdout_blends = [], []
    checks = []
    for item in report["accepted_factors"]:
        assert item["accepted"]
        branch, identity = item["branch"], item["id"]
        signal = evaluate(compile_expression(item["expression"]), panel) * item["direction"]
        development_signal = signal.loc[selection.index]
        nav = reference_nav(development_signal, selection)
        observed = pd.read_csv(directory / branch / identity / "selection_daily.csv")
        max_nav = max(max_nav, float(np.max(abs(nav - observed.net_nav.to_numpy()))))
        observed_ic = pd.read_csv(
            directory / branch / identity / "discovery_ic.csv", index_col=0
        ).iloc[:, 0]
        observed_ic.index = pd.to_datetime(observed_ic.index)
        independent_ic = []
        for date in observed_ic.dropna().index:
            valid = np.isfinite(signal.loc[date]) & np.isfinite(labels.loc[date])
            value = float(spearmanr(signal.loc[date, valid], labels.loc[date, valid]).statistic)
            independent_ic.append(value)
            max_ic = max(max_ic, abs(value - observed_ic.loc[date]))
        independent_periods = {"selection": metrics(nav, benchmark)}
        for key, start, end in [
            ("year2014", "2014-01-01", "2014-12-31"),
            ("year2015", "2015-01-01", "2015-12-31"),
            ("last9m", "2015-04-01", "2015-12-31"),
            ("last12m", "2015-01-01", "2015-12-31"),
        ]:
            positions = np.flatnonzero((selection.index >= start) & (selection.index <= end))
            a, b = max(0, positions[0] - 1), positions[-1] + 1
            independent_periods[key] = metrics(nav[a:b], benchmark[a:b])
        for period, numbers in independent_periods.items():
            for key, value in numbers.items():
                max_metric = max(max_metric, abs(value - item["periods"][period][key]))
        correlations = []
        for other in prior:
            daily_corr = []
            for date in selection.index:
                a, b = development_signal.loc[date], other.loc[date]
                valid = np.isfinite(a) & np.isfinite(b)
                if valid.sum() >= 20:
                    daily_corr.append(abs(spearmanr(a[valid], b[valid]).statistic))
            assert len(daily_corr) >= 120
            correlations.append(float(np.mean(daily_corr)))
        correlation = max(correlations) if correlations else None
        if correlations:
            max_corr = max(max_corr, abs(correlation - item["metrics"]["max_correlation"]))
        independent = {
            "abs_ic": abs(float(np.mean(independent_ic))),
            "year1_excess": independent_periods["year2014"]["annual_excess"],
            "year2_excess": independent_periods["year2015"]["annual_excess"],
            "year1_sharpe": independent_periods["year2014"]["sharpe"],
            "year2_sharpe": independent_periods["year2015"]["sharpe"],
            "calmar": independent_periods["selection"]["calmar"],
            "last9m_excess": independent_periods["last9m"]["annual_excess"],
            "last12m_excess": independent_periods["last12m"]["annual_excess"],
            "max_correlation": correlation,
            "coverage": float(
                signal.loc[panel["open"].index[120] : "2015-12-31"].notna().to_numpy().mean()
            ),
            "sample_check": int(
                len(independent_ic) >= 120
                and len(selection.loc["2014"].iloc[1:]) >= 200
                and len(selection.loc["2015"]) >= 200
            ),
        }
        gates = evaluate_gates(independent)
        if not prior:
            gates[8]["status"] = "not_applicable"
        assert all(g["status"] in {"passed", "not_applicable"} for g in gates)
        prior.append(development_signal)
        holdout_signal = signal.loc[holdout.index]
        test_nav = reference_nav(holdout_signal, holdout)
        test_daily = pd.read_csv(directory / "LIBRARY" / identity / "holdout_daily.csv")
        max_nav = max(max_nav, float(np.max(abs(test_nav - test_daily.nav.to_numpy()))))
        expected = metrics(test_nav, holdout_benchmark)
        actual = next(f for f in report["holdout"]["LIBRARY"]["factors"] if f["id"] == identity)
        for key, value in expected.items():
            max_metric = max(max_metric, abs(value - actual[key]))
        selection_blends.append(development_signal.rank(axis=1, pct=True))
        holdout_blends.append(holdout_signal.rank(axis=1, pct=True))
        checks.append({"id": identity, "gates_passed": True, "holdout_nav_checked": True})
    for name, cap in [("LIBRARY", len(prior)), ("TOP5", 5)]:
        parts = holdout_blends[:cap]
        if parts:
            nav = reference_nav(sum(parts) / len(parts), holdout)
            actual = pd.read_csv(directory / name / "composite_holdout.csv")
            max_nav = max(max_nav, float(np.max(abs(nav - actual.nav.to_numpy()))))
    result.update(
        accepted_count=len(checks),
        accepted_factor_checks=checks,
        max_ic_absolute_error=max(max_ic, result["max_ic_absolute_error"]),
        max_nav_absolute_error=max(max_nav, result["max_nav_absolute_error"]),
        max_metric_absolute_error=max_metric,
        max_correlation_absolute_error=max_corr,
        ic_reference="SciPy Spearman: six baselines plus every admitted factor",
        portfolio_reference="Independent scalar holdings and SciPy brentq: baseline, admitted selection/holdout, composites",
        freeze_hash_verified=True,
    )
    assert result["max_ic_absolute_error"] < 1e-10
    assert result["max_nav_absolute_error"] < 1e-10
    assert max_metric < 1e-10 and max_corr < 1e-10
    write_json(directory / "verification.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--data", type=Path, default=Path("data/stocknet-330708b5"))
    args = parser.parse_args()
    verify_expanded(args.experiment, args.data)
