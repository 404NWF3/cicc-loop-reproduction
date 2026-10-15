import pandas as pd
import pytest

from loop_research.errors import ResearchError
from loop_research.factors.dsl import compile_expression, evaluate
from loop_research.factors.fsa import FrequentSubtreeAvoidance


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('id')",
        "close.__class__",
        "close[0]",
        "close + open",
        "delay(close, -1)",
        "ts_mean(close, 0)",
        "ts_mean(close, 20.5)",
        "add(close, volume)",
        "add(cs_rank(1), close)",
        "mul(ts_mean(add(1, 2), 5), close)",
        "True",
        "ts_mean(ts_mean(ts_mean(close, 60), 60), 5)",
        "safe_div(close, 1e999)",
    ],
)
def test_unsafe_or_semantically_invalid_expressions_are_rejected(expression):
    with pytest.raises(ResearchError):
        compile_expression(expression)


@pytest.mark.parametrize(
    "expression", ["ts_mean(ret1, 20)", "cs_rank(gap)", "ts_corr(ret1, rel_volume, 10)"]
)
def test_future_prices_cannot_change_past_features(panel, expression):
    node = compile_expression(expression)
    before = evaluate(node, panel)
    changed = {key: value.copy() for key, value in panel.items()}
    for frame in changed.values():
        frame.iloc[60:] *= 4.5
    after = evaluate(node, changed)
    pd.testing.assert_frame_equal(before.iloc[:60], after.iloc[:60])


def test_rolling_never_crosses_symbols_and_handles_zero_division(panel):
    actual = evaluate(compile_expression("ts_mean(close, 3)"), panel)
    assert actual.iloc[2, 0] == pytest.approx(101)
    assert actual.iloc[2, 1] == pytest.approx(200.3)
    assert actual.iloc[:2].isna().all().all()
    assert evaluate(compile_expression("safe_div(close, 0)"), panel).isna().all().all()


def test_fingerprints_and_subtree_parameter_normalization():
    first = compile_expression("add(gap, ret1)")
    assert first.fingerprint == compile_expression("add(ret1, gap)").fingerprint
    a, b = compile_expression("ts_mean(gap, 5)"), compile_expression("ts_mean(gap, 20)")
    assert a.fingerprint != b.fingerprint
    assert a.subtrees() == b.subtrees()
    fsa = FrequentSubtreeAvoidance()
    for _ in range(50):
        fsa.observe(a)
    assert fsa.inspect(b, 5)
    assert not fsa.inspect(compile_expression("ts_mean(intraday_range, 10)"), 5)
    recovered = FrequentSubtreeAvoidance(fsa.snapshot())
    assert recovered.inspect(b, 6) == fsa.inspect(b, 6)
