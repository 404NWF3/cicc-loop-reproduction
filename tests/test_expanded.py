import numpy as np
import pandas as pd

from loop_research.backtest.gates import GATES
from loop_research.experiments.expanded import PROTOCOL, initial_plan, is_degenerate
from loop_research.factors.dsl import compile_expression


def test_near_constant_roundoff_cannot_be_used_as_stock_ranking():
    dates = pd.date_range("2013-01-01", periods=20)
    noise = np.random.default_rng(17).normal(0, 1e-14, (20, 50))
    assert is_degenerate(pd.DataFrame(1 + noise, index=dates), dates[0])
    assert not is_degenerate(pd.DataFrame(noise * 1e10, index=dates), dates[0])


def test_expansion_preserves_gates_costs_and_generates_a_fixed_typed_plan():
    assert PROTOCOL["gates"] == GATES
    assert PROTOCOL["cost_one_side"] == 0.001
    assert PROTOCOL["rebalance"] == 5
    assert PROTOCOL["max_cny"] == 40
    first, second = initial_plan(), initial_plan()
    assert first == second
    assert len(first) == 3972
    for row in first:
        node = compile_expression(row["expression"])
        assert node.lookback <= 120
        assert node.depth <= 6
