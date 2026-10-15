"""Development-only deterministic selection and a separate frozen holdout evaluator."""

from pathlib import Path

import numpy as np
import pandas as pd

from loop_research.backtest.engine import simulate
from loop_research.backtest.gates import evaluate_gates
from loop_research.backtest.metrics import forward_returns, rank_ic, relative_metrics
from loop_research.experiments.data import DISCOVERY_END, SELECTION_END, write_json
from loop_research.factors.dsl import Node, evaluate


def finite(value):
    return float(value) if value is not None and np.isfinite(value) else None


def segment_metrics(portfolio: pd.DataFrame, benchmark: pd.DataFrame, start: str, end: str) -> dict:
    dates = portfolio.index[(portfolio.index >= start) & (portfolio.index <= end)]
    if not len(dates):
        return relative_metrics(pd.Series(dtype=float), pd.Series(dtype=float))
    position = portfolio.index.get_loc(dates[0])
    # Include the preceding valuation to count the first return/cost of an interior period.
    first = portfolio.index[max(0, position - 1)]
    return relative_metrics(
        portfolio.nav.loc[first : dates[-1]], benchmark.nav.loc[first : dates[-1]]
    )


class DevelopmentEvaluator:
    def __init__(self, panel: dict, destination: Path | None):
        if panel["open"].index.max() > pd.Timestamp(SELECTION_END):
            raise ValueError("Development evaluator cannot read holdout prices")
        self.panel, self.destination = panel, destination
        self.discovery_opens = panel["open"].loc[:DISCOVERY_END]
        self.labels = forward_returns(self.discovery_opens)
        self.opens = panel["open"].loc["2014-01-01":SELECTION_END]
        self.benchmark = simulate(self.opens * 0 + 1, self.opens, top_fraction=1)
        self.gross_benchmark = simulate(self.opens * 0 + 1, self.opens, top_fraction=1, cost=0)
        self.warmup_end = panel["open"].index[120]
        if destination is not None:
            self.benchmark.to_csv(destination / "benchmark_selection.csv", float_format="%.12g")

    def compute(
        self,
        candidate: dict,
        node: Node,
        library: list[pd.DataFrame],
        *,
        raw_signal: pd.DataFrame | None = None,
        raw_ic: pd.Series | None = None,
        persist: bool = True,
        include_series: bool = False,
    ):
        if raw_signal is None:
            raw_signal = evaluate(node, self.panel)
        if raw_ic is None:
            raw_ic = rank_ic(raw_signal.loc[:DISCOVERY_END], self.labels).loc[self.warmup_end :]
        raw_mean = finite(raw_ic.mean())
        direction = -1 if raw_mean is not None and raw_mean < 0 else 1
        signal = raw_signal * direction
        ic = raw_ic * direction
        selected = signal.reindex(self.opens.index)
        portfolio = simulate(selected, self.opens)
        gross = simulate(selected, self.opens, cost=0)
        periods = {
            "selection": relative_metrics(portfolio.nav, self.benchmark.nav),
            "selection_gross": relative_metrics(gross.nav, self.gross_benchmark.nav),
            "year2014": segment_metrics(portfolio, self.benchmark, "2014-01-01", "2014-12-31"),
            "year2015": segment_metrics(portfolio, self.benchmark, "2015-01-01", "2015-12-31"),
            "last9m": segment_metrics(portfolio, self.benchmark, "2015-04-01", SELECTION_END),
            "last12m": segment_metrics(portfolio, self.benchmark, "2015-01-01", SELECTION_END),
        }
        correlations = []
        for other in library:
            corr = rank_ic(selected, other).abs().dropna()
            correlations.append(float(corr.mean()) if len(corr) >= 120 else None)
        complete_corr = all(x is not None for x in correlations)
        max_corr = max(correlations) if correlations and complete_corr else None
        metrics = {
            "abs_ic": abs(raw_mean) if raw_mean is not None else None,
            "year1_excess": periods["year2014"]["annual_excess"],
            "year2_excess": periods["year2015"]["annual_excess"],
            "year1_sharpe": periods["year2014"]["sharpe"],
            "year2_sharpe": periods["year2015"]["sharpe"],
            "calmar": periods["selection"]["calmar"],
            "last9m_excess": periods["last9m"]["annual_excess"],
            "last12m_excess": periods["last12m"]["annual_excess"],
            "max_correlation": max_corr,
            "coverage": float(signal.loc[self.warmup_end :].notna().to_numpy().mean()),
            "sample_check": int(
                ic.notna().sum() >= 120
                and len(portfolio.loc["2014"].iloc[1:]) >= 200
                and len(portfolio.loc["2015"]) >= 200
            ),
        }
        gates = evaluate_gates(metrics)
        if not library:
            gates[8].update(status="not_applicable", value=None, reason="empty_library")
        elif not complete_corr:
            gates[8].update(reason="insufficient_common_dates")
        accepted = all(g["status"] in {"passed", "not_applicable"} for g in gates)
        candidate.update(
            direction=direction,
            discovery_raw_ic=raw_mean,
            discovery_ic=finite(ic.mean()),
            icir=finite(ic.mean() / ic.std(ddof=1)) if ic.std(ddof=1) > 1e-12 else None,
            ic_days=int(ic.notna().sum()),
            metrics=metrics,
            periods=periods,
            gates=gates,
            accepted=accepted,
            status="accepted" if accepted else "gate_rejected",
            rejection_codes=[
                g["id"] for g in gates if g["status"] not in {"passed", "not_applicable"}
            ],
            turnover_two_sided_mean=float(portfolio.turnover.mean()),
            turnover_one_sided_mean=float(portfolio.turnover.mean() / 2),
        )
        if include_series:
            dates = portfolio.index[::5].union(portfolio.index[-1:])
            candidate["series"] = [
                {
                    "date": str(date.date()),
                    "nav": float(portfolio.loc[date, "nav"]),
                    "benchmark": float(self.benchmark.loc[date, "nav"]),
                    "relative": float(portfolio.loc[date, "nav"] / self.benchmark.loc[date, "nav"]),
                }
                for date in dates
            ]
        if not persist:
            return selected
        output = self.destination / candidate["id"]
        output.mkdir()
        pd.DataFrame(
            {
                "net_nav": portfolio.nav,
                "gross_nav": gross.nav,
                "benchmark_net_nav": self.benchmark.nav,
                "benchmark_gross_nav": self.gross_benchmark.nav,
                "net_return": portfolio["return"],
                "cost": portfolio.cost,
                "turnover_two_sided": portfolio.turnover,
            }
        ).to_csv(output / "selection_daily.csv", float_format="%.12g")
        ic.to_csv(output / "discovery_ic.csv", float_format="%.12g")
        write_json(output / "result.json", candidate)
        return selected


def evaluate_holdout(panel: dict, branches: dict, freeze: dict, destination: Path) -> dict:
    from loop_research.factors.dsl import compile_expression

    opens = panel["open"].loc["2016-01-01":]
    benchmark = simulate(opens * 0 + 1, opens, top_fraction=1)
    benchmark.to_csv(destination / "benchmark_holdout.csv", float_format="%.12g")
    results = {}
    for branch, frozen in freeze["branches"].items():
        signals, factors = [], []
        for item in frozen:
            node = compile_expression(item["expression"])
            signal = (evaluate(node, panel) * item["direction"]).reindex(opens.index)
            portfolio = simulate(signal, opens)
            metrics = relative_metrics(portfolio.nav, benchmark.nav)
            labels = forward_returns(opens)
            ic = rank_ic(signal, labels)
            factors.append(
                {
                    "id": item["id"],
                    "expression": item["expression"],
                    "direction": item["direction"],
                    **metrics,
                    "rank_ic": finite(ic.mean()),
                    "ic_days": int(ic.notna().sum()),
                }
            )
            signals.append(signal.rank(axis=1, pct=True))
            folder = destination / branch / item["id"]
            folder.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(
                {
                    "nav": portfolio.nav,
                    "benchmark_nav": benchmark.nav,
                    "cost": portfolio.cost,
                    "turnover": portfolio.turnover,
                }
            ).to_csv(folder / "holdout_daily.csv", float_format="%.12g")
            ic.to_csv(folder / "holdout_ic.csv", float_format="%.12g")
        composite = None
        if signals:
            # Strict equal-weight rank blend; a missing constituent remains missing.
            blend = sum(signals) / len(signals)
            portfolio = simulate(blend, opens)
            composite = relative_metrics(portfolio.nav, benchmark.nav)
            composite["factor_count"] = len(signals)
            portfolio.to_csv(destination / branch / "composite_holdout.csv", float_format="%.12g")
        results[branch] = {
            "factors": factors,
            "composite": composite,
            "status": "evaluated" if signals else "no_accepted_factors",
        }
    return results
