import json
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from loop_research.backtest.metrics import rank_ic
from loop_research.errors import ResearchError
from loop_research.experiments.evaluation import DevelopmentEvaluator
from loop_research.experiments.runner import json_hash, validate_config
from loop_research.models.ledger import PersistentBudget


def test_money_cap_persists_after_restart_and_unknown_usage(tmp_path):
    path = tmp_path / "budget.sqlite3"
    ledger = PersistentBudget(path, max_cny=0.008)
    ledger.reserve(700)
    ledger.settle(700, None)
    reopened = PersistentBudget(path, max_cny=40)
    with pytest.raises(ResearchError, match="预算"):
        reopened.reserve(301)
    reopened.reserve(300)
    with pytest.raises(ResearchError, match="预算"):
        reopened.reserve(1)
    assert reopened.summary()["cost_upper_bound_cny"] == pytest.approx(0.008)
    assert reopened.summary()["unresolved_requests"] == 2


def test_shared_ledger_serializes_concurrent_reservations(tmp_path):
    path = tmp_path / "budget.sqlite3"
    PersistentBudget(path, max_requests=1)

    def send(_):
        try:
            PersistentBudget(path).reserve(100)
            return True
        except ResearchError:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(send, range(4))) == 1


def test_settled_usage_and_retries_still_consume_request_quota(tmp_path):
    ledger = PersistentBudget(tmp_path / "budget.sqlite3", max_requests=2)
    ledger.reserve(1000)
    ledger.settle(1000, 150)
    ledger.reserve(1000)  # retry with an unknown outcome keeps its reservation
    ledger.settle(1000, "bad-usage")
    assert ledger.summary()["tokens_charged_or_reserved"] == 1150
    with pytest.raises(ResearchError):
        ledger.reserve(10)


def test_cross_sectional_ic_matches_scipy_with_ties_missing_and_infinity():
    rng = np.random.default_rng(2026)
    left = pd.DataFrame(rng.integers(0, 8, (12, 35)).astype(float))
    right = pd.DataFrame(rng.normal(size=(12, 35)))
    left.iloc[0, :18] = np.nan
    left.iloc[1, 0] = np.inf
    right.iloc[2, :5] = np.nan
    left.iloc[3] = 1
    observed = rank_ic(left, right)
    for row in left.index:
        valid = np.isfinite(left.loc[row]) & np.isfinite(right.loc[row])
        if valid.sum() < 20 or left.loc[row, valid].nunique() < 2:
            assert np.isnan(observed.loc[row])
        else:
            expected = spearmanr(left.loc[row, valid], right.loc[row, valid]).statistic
            assert observed.loc[row] == pytest.approx(expected, abs=1e-12)


def test_development_rejects_holdout_before_any_computation(tmp_path):
    with pytest.raises(ValueError, match="holdout"):
        DevelopmentEvaluator({"open": pd.DataFrame(index=pd.to_datetime(["2016-01-04"]))}, tmp_path)


def test_protocol_rejects_silent_threshold_or_timing_changes():
    from pathlib import Path

    import yaml

    config = json.loads(
        json.dumps(yaml.safe_load(Path("configs/local_experiment.yaml").read_text()), default=str)
    )
    validate_config(config)
    original = json_hash(config)
    config["cost_one_side"] = 0
    assert json_hash(config) != original
    with pytest.raises(ValueError, match="protocol"):
        validate_config(config)
