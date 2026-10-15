import numpy as np
import pandas as pd

from loop_research.errors import ResearchError

REQUIRED = {"date", "symbol", "open", "high", "low", "close", "volume"}


def validate_frame(frame: pd.DataFrame) -> dict:
    issues = []
    missing = REQUIRED - set(frame.columns)
    if missing:
        return {"valid": False, "rows": len(frame), "issues": [f"缺少列：{sorted(missing)}"]}
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any():
        issues.append("存在无效日期")
    if frame.assign(date=dates).duplicated(["date", "symbol"]).any():
        issues.append("存在重复的 date/symbol 键")
    if frame["symbol"].isna().any() or frame["symbol"].astype(str).str.strip().eq("").any():
        issues.append("存在空股票标识")
    numbers = frame[["open", "high", "low", "close", "volume"]].apply(
        pd.to_numeric, errors="coerce"
    )
    if not np.isfinite(numbers.to_numpy()).all():
        issues.append("存在缺失或非有限数值")
    if (numbers[["open", "high", "low", "close"]] <= 0).any().any():
        issues.append("价格必须为正数")
    if (numbers["volume"] < 0).any():
        issues.append("成交量不能为负数")
    if (
        (numbers.high < numbers[["open", "close", "low"]].max(axis=1))
        | (numbers.low > numbers[["open", "close", "high"]].min(axis=1))
    ).any():
        issues.append("OHLC 高低价关系不成立")
    if len(frame) == 0:
        issues.append("数据为空")
    return {
        "valid": not issues,
        "rows": len(frame),
        "symbols": frame.symbol.nunique(),
        "start": str(dates.min().date()) if len(dates) and dates.notna().any() else None,
        "end": str(dates.max().date()) if len(dates) and dates.notna().any() else None,
        "issues": issues,
        "scope": "schema_and_prices_only",
        "note": "仅校验结构与价格关系；复权、幸存者偏差及研究区间尚需另行确认。",
    }


def to_panel(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    report = validate_frame(frame)
    if not report["valid"]:
        raise ResearchError("invalid_dataset", "数据校验失败。", 422, report)
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["symbol"] = data["symbol"].astype(str)
    data = data.sort_values(["date", "symbol"]).set_index(["date", "symbol"])
    return {
        field: data[field].astype(float).unstack("symbol")
        for field in REQUIRED - {"date", "symbol"}
    }
