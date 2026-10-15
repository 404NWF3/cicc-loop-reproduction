import math

import numpy as np
import pandas as pd


def forward_returns(opens: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    if horizon < 1:
        raise ValueError("horizon must be positive")
    return opens.shift(-(horizon + 1)) / opens.shift(-1) - 1


def rank_ic(signal: pd.DataFrame, labels: pd.DataFrame, min_assets: int = 20) -> pd.Series:
    result = {}
    for date in signal.index.intersection(labels.index):
        pair = pd.concat([signal.loc[date], labels.loc[date]], axis=1)
        pair = pair.replace([np.inf, -np.inf], np.nan).dropna()
        if len(pair) < min_assets or (pair.nunique() < 2).any():
            result[date] = np.nan
        else:
            result[date] = pair.iloc[:, 0].rank().corr(pair.iloc[:, 1].rank())
    return pd.Series(result, dtype=float, name="rank_ic")


def relative_metrics(portfolio: pd.Series, benchmark: pd.Series) -> dict:
    data = pd.concat([portfolio, benchmark], axis=1).dropna()
    if len(data) < 3 or (data <= 0).any().any():
        return {"annual_excess": None, "sharpe": None, "max_drawdown": None, "calmar": None}
    relative = data.iloc[:, 0] / data.iloc[:, 1]
    relative = relative / relative.iloc[0]
    returns = relative.pct_change().dropna()
    annual = float(relative.iloc[-1] ** (252 / len(returns)) - 1)
    std = float(returns.std(ddof=1))
    sharpe = float(returns.mean() / std * math.sqrt(252)) if std > 1e-12 else None
    drawdown = float((relative / relative.cummax() - 1).min())
    calmar = annual / abs(drawdown) if drawdown < -1e-12 else None
    return {"annual_excess": annual, "sharpe": sharpe, "max_drawdown": drawdown, "calmar": calmar}
