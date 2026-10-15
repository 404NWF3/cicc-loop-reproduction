"""A small, self-financing open-to-open portfolio simulator.

This primitive is not connected to fixture tasks and does not fetch market data.
"""

import math

import numpy as np
import pandas as pd

from loop_research.errors import ResearchError


def simulate(
    signal: pd.DataFrame,
    opens: pd.DataFrame,
    *,
    rebalance: int = 5,
    top_fraction: float = 0.2,
    cost: float = 0.001,
) -> pd.DataFrame:
    if (
        not 0 < top_fraction <= 1
        or not 0 <= cost < 0.1
        or type(rebalance) is not int
        or rebalance < 1
    ):
        raise ValueError("Invalid portfolio parameters")
    if opens.empty or opens.columns.has_duplicates:
        raise ValueError("Prices must contain unique symbols and a nonempty trading calendar")
    if not opens.index.equals(signal.index) or not opens.columns.equals(signal.columns):
        raise ValueError("Signals and prices must share the exact trading calendar and symbols")
    if not opens.index.is_monotonic_increasing or opens.index.has_duplicates:
        raise ValueError("The trading calendar must be sorted and unique")
    shares = np.zeros(len(opens.columns))
    cash = 1.0
    records = []
    for i, date in enumerate(opens.index):
        prices = opens.loc[date].to_numpy(dtype=float)
        available = np.isfinite(prices) & (prices > 0)
        if ((shares != 0) & ~available).any():
            raise ResearchError("data_gap", "已持仓股票缺少有效估值/成交价格。", 422)
        prices = np.where(available, prices, 0)
        holdings = shares * prices
        nav_before = float(cash + holdings.sum())
        fee, turnover = 0.0, 0.0
        liquidate = i == len(opens.index) - 1
        rebalance_today = i >= 1 and (i - 1) % rebalance == 0
        if rebalance_today or liquidate:
            weights = np.zeros(len(prices))
            if not liquidate:
                scores = signal.iloc[i - 1].replace([np.inf, -np.inf], np.nan)
                eligible = scores.notna().to_numpy() & available
                ordered = sorted(
                    np.flatnonzero(eligible),
                    key=lambda j: (-float(scores.iloc[j]), str(opens.columns[j])),
                )
                if ordered:
                    chosen = ordered[: max(1, math.ceil(len(ordered) * top_fraction))]
                    weights[chosen] = 1 / len(chosen)
            # Solve post_trade_nav + fees(post_trade_nav) = pre_trade_nav.
            nav_after = nav_before
            if cost:
                low, high = 0.0, nav_before
                for _ in range(60):
                    mid = (low + high) / 2
                    amount = np.abs(mid * weights - holdings).sum()
                    if mid + cost * amount > nav_before:
                        high = mid
                    else:
                        low = mid
                nav_after = (low + high) / 2
            amount = float(np.abs(nav_after * weights - holdings).sum())
            fee = cost * amount
            turnover = amount / nav_before if nav_before else 0.0
            shares = np.divide(
                nav_after * weights, prices, out=np.zeros_like(prices), where=available
            )
            cash = nav_before - fee - float((shares * prices).sum())
        nav = cash + float((shares * prices).sum())
        records.append({"date": date, "nav": nav, "cost": fee, "turnover": turnover})
    result = pd.DataFrame(records).set_index("date")
    result["return"] = result.nav.pct_change().fillna(0.0)
    return result
