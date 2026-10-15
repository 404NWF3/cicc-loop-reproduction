import numpy as np
import pandas as pd
import pytest

from loop_research.backtest.engine import simulate
from loop_research.backtest.gates import evaluate_gates
from loop_research.backtest.metrics import forward_returns, rank_ic, relative_metrics
from loop_research.errors import ResearchError


def test_next_open_entry_and_entry_exit_costs():
    dates = pd.bdate_range("2020-01-01", periods=4)
    opens = pd.DataFrame({"A": [10000, 100, 110, 121], "B": [100, 100, 100, 100]}, index=dates)
    signal = pd.DataFrame({"A": [1, 0, 0, 0], "B": [0, 1, 1, 1]}, index=dates)
    result = simulate(signal, opens, top_fraction=0.5, cost=0.001)
    assert result.iloc[1].nav == pytest.approx(1 / 1.001)
    assert result.iloc[-1].nav == pytest.approx((1 / 1.001) * 1.21 * 0.999)
    assert result.iloc[0].cost == 0
    assert result.iloc[1].cost > 0 and result.iloc[-1].cost > 0


def test_turnover_accounts_for_price_drift():
    dates = pd.bdate_range("2020-01-01", periods=4)
    opens = pd.DataFrame({"A": [100, 100, 200, 200], "B": [100, 100, 100, 100]}, index=dates)
    signal = pd.DataFrame(1.0, index=dates, columns=opens.columns)
    result = simulate(signal, opens, rebalance=1, top_fraction=1, cost=0)
    assert result.iloc[2].turnover == pytest.approx(1 / 3)
    assert result.iloc[-1].nav == pytest.approx(1.5)


def test_held_stock_without_exit_price_is_not_silently_dropped():
    dates = pd.bdate_range("2020-01-01", periods=3)
    opens = pd.DataFrame({"A": [100, 100, np.nan]}, index=dates)
    with pytest.raises(ResearchError, match="有效估值"):
        simulate(opens.notna().astype(float), opens)


def test_labels_include_execution_lag_and_preserve_unavailable_tail(panel):
    labels = forward_returns(panel["open"], 5)
    assert labels.iloc[0, 0] == pytest.approx(
        panel["open"].iloc[6, 0] / panel["open"].iloc[1, 0] - 1
    )
    assert labels.iloc[-6:].isna().all().all()


def test_rank_ic_and_undefined_metrics():
    dates = pd.date_range("2020-01-01", periods=2)
    signal = pd.DataFrame([[1, 2, 3], [1, 1, 1]], index=dates)
    labels = pd.DataFrame([[0.3, 0.2, 0.1], [0.1, 0.2, 0.3]], index=dates)
    ic = rank_ic(signal, labels, min_assets=3)
    assert ic.iloc[0] == pytest.approx(-1)
    assert np.isnan(ic.iloc[1])
    flat = pd.Series([1.0] * 10)
    metrics = relative_metrics(flat, flat)
    assert metrics["sharpe"] is None and metrics["calmar"] is None


def test_unevaluated_nonfinite_and_boundary_gates_do_not_pass():
    assert all(g["status"] == "not_evaluated" for g in evaluate_gates({}))
    gates = evaluate_gates({"abs_ic": 0.03, "calmar": float("inf"), "coverage": 0.9})
    assert gates[0]["status"] == "failed"
    assert gates[5]["status"] == "not_evaluated"
    assert gates[9]["status"] == "passed"
