"""Parse a small expression language without evaluating Python code."""

import ast
import hashlib
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from loop_research.errors import ResearchError

DIMENSIONLESS = (0, 0)
FIELDS = {
    "open": ((1, 0), 0),
    "high": ((1, 0), 0),
    "low": ((1, 0), 0),
    "close": ((1, 0), 0),
    "volume": ((0, 1), 0),
    "ret1": (DIMENSIONLESS, 1),
    "gap": (DIMENSIONLESS, 1),
    "intraday_return": (DIMENSIONLESS, 0),
    "intraday_range": (DIMENSIONLESS, 1),
    "upper_shadow": (DIMENSIONLESS, 0),
    "lower_shadow": (DIMENSIONLESS, 0),
    "rel_volume": (DIMENSIONLESS, 19),
}
ARITIES = {
    "add": 2,
    "sub": 2,
    "mul": 2,
    "safe_div": 2,
    "neg": 1,
    "abs": 1,
    "cs_rank": 1,
    "cs_zscore": 1,
    "delay": 2,
    "delta": 2,
    "ts_mean": 2,
    "ts_std": 2,
    "ts_min": 2,
    "ts_max": 2,
    "ts_rank": 2,
    "ts_corr": 3,
}
WINDOWS = {1, 2, 3, 5, 10, 20, 40, 60}


def invalid(message: str) -> ResearchError:
    return ResearchError("invalid_expression", message, 422)


@dataclass(frozen=True)
class Node:
    op: str
    value: str | float | None = None
    args: tuple["Node", ...] = ()
    unit: tuple[int, int] = DIMENSIONLESS
    lookback: int = 0

    @property
    def size(self) -> int:
        return 1 + sum(a.size for a in self.args)

    @property
    def depth(self) -> int:
        return 1 + max((a.depth for a in self.args), default=0)

    @property
    def is_series(self) -> bool:
        return self.op == "field" or any(a.is_series for a in self.args)

    def canonical(self, skeleton: bool = False) -> str:
        if self.op == "field":
            return str(self.value)
        if self.op == "number":
            return "#" if skeleton else format(float(self.value), ".12g")
        children = [a.canonical(skeleton) for a in self.args]
        if self.op in {"add", "mul"}:
            children.sort()
        return f"{self.op}({', '.join(children)})"

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()

    def as_dict(self) -> dict:
        return {
            "operator": self.op,
            "value": self.value,
            "unit": list(self.unit),
            "lookback": self.lookback,
            "children": [a.as_dict() for a in self.args],
        }

    def subtrees(self) -> set[str]:
        result = set()
        if self.size >= 3 and self.op not in {"cs_rank", "cs_zscore", "neg", "abs"}:
            result.add(self.canonical(skeleton=True))
        for arg in self.args:
            result.update(arg.subtrees())
        return result


def compile_expression(expression: str) -> Node:
    if not expression.strip() or len(expression) > 2000:
        raise invalid("表达式不能为空，且不能超过 2000 个字符。")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise invalid("表达式语法不正确。") from exc
    if len(list(ast.walk(tree))) > 180:
        raise invalid("表达式过于复杂。")

    def visit(item: ast.AST, depth: int = 1) -> Node:
        if depth > 6:
            raise invalid("表达式深度不能超过 6。")
        if isinstance(item, ast.Name) and item.id in FIELDS:
            unit, lookback = FIELDS[item.id]
            return Node("field", item.id, unit=unit, lookback=lookback)
        if isinstance(item, ast.Constant) and type(item.value) in {float, int}:
            if not math.isfinite(item.value) or abs(item.value) > 100:
                raise invalid("常数必须为绝对值不超过 100 的有限数字。")
            return Node("number", float(item.value))
        if isinstance(item, ast.UnaryOp) and isinstance(item.op, ast.USub):
            if isinstance(item.operand, ast.Constant):
                number = visit(item.operand, depth + 1)
                return Node("number", -float(number.value))
        if not isinstance(item, ast.Call) or not isinstance(item.func, ast.Name):
            raise invalid("只允许白名单字段、数字和函数调用，禁止 Python 代码。")
        op = item.func.id
        if op not in ARITIES or len(item.args) != ARITIES[op] or item.keywords:
            raise invalid(f"不支持的算子或参数数量：{op}。")
        args = tuple(visit(a, depth + 1) for a in item.args)
        unit = args[0].unit
        lookback = max(a.lookback for a in args)
        if op in {"add", "sub"} and args[0].unit != args[1].unit:
            raise invalid("加减运算的两侧必须具有相同量纲。")
        if op in {"mul", "safe_div"}:
            sign = 1 if op == "mul" else -1
            unit = tuple(a + sign * b for a, b in zip(args[0].unit, args[1].unit))
        if op.startswith("ts_") or op in {"delay", "delta"}:
            window = args[-1]
            if window.op != "number" or window.value not in WINDOWS:
                raise invalid(f"时间窗口必须是 {sorted(WINDOWS)} 中的正整数。")
            if not args[0].is_series or (op == "ts_corr" and not args[1].is_series):
                raise invalid("时序算子必须作用于序列。")
            lookback += int(window.value) if op in {"delay", "delta"} else int(window.value) - 1
        if op in {"ts_rank", "ts_corr", "cs_rank", "cs_zscore"}:
            unit = DIMENSIONLESS
        if op in {"cs_rank", "cs_zscore"} and not args[0].is_series:
            raise invalid("截面算子必须作用于序列。")
        node = Node(op, args=args, unit=unit, lookback=lookback)
        if node.lookback > 120 or node.size > 32:
            raise invalid("累计回看长度不能超过 120，节点数不能超过 32。")
        return node

    result = visit(tree.body)
    if not any(isinstance(n, ast.Name) and n.id in FIELDS for n in ast.walk(tree)):
        raise invalid("因子必须包含至少一个数据字段。")
    return result


def _divide(a, b):
    if np.isscalar(b):
        return a / b if abs(b) >= 1e-12 else a * np.nan
    return a / b.where(b.abs() >= 1e-12)


def prepare_fields(panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    fields = dict(panel)
    o, h, low, c, v = (panel[k] for k in ("open", "high", "low", "close", "volume"))
    fields.update(
        {
            "ret1": _divide(c, c.shift(1)) - 1,
            "gap": _divide(o, c.shift(1)) - 1,
            "intraday_return": _divide(c - o, o),
            "intraday_range": _divide(h - low, c.shift(1)),
            "upper_shadow": _divide(h - np.maximum(o, c), o),
            "lower_shadow": _divide(np.minimum(o, c) - low, o),
            "rel_volume": _divide(v, v.rolling(20, min_periods=20).mean()),
        }
    )
    return fields


def evaluate(node: Node, panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(panel):
        raise invalid("数据必须包含全部 OHLCV 字段。")
    reference = panel["close"]
    if (
        reference.empty
        or not reference.index.is_monotonic_increasing
        or reference.index.has_duplicates
    ):
        raise invalid("数据必须具有非空、递增且唯一的交易日索引。")
    if reference.columns.has_duplicates or any(
        not panel[key].index.equals(reference.index)
        or not panel[key].columns.equals(reference.columns)
        for key in required
    ):
        raise invalid("所有字段必须使用相同的交易日和唯一股票列。")
    fields = prepare_fields(panel)

    def visit(n: Node):
        if n.op == "field":
            return fields[str(n.value)]
        if n.op == "number":
            return float(n.value)
        args = [visit(a) for a in n.args]
        x, op = args[0], n.op
        if op == "add":
            return x + args[1]
        if op == "sub":
            return x - args[1]
        if op == "mul":
            return x * args[1]
        if op == "safe_div":
            return _divide(x, args[1])
        if op == "neg":
            return -x
        if op == "abs":
            return abs(x)
        if op == "cs_rank":
            return x.rank(axis=1, pct=True, method="average")
        if op == "cs_zscore":
            std = x.std(axis=1).replace(0, np.nan)
            return x.sub(x.mean(axis=1), axis=0).div(std, axis=0)
        window = int(args[-1])
        if op == "delay":
            return x.shift(window)
        if op == "delta":
            return x - x.shift(window)
        rolling = x.rolling(window, min_periods=window)
        if op == "ts_mean":
            return rolling.mean()
        if op == "ts_std":
            return rolling.std(ddof=1)
        if op == "ts_min":
            return rolling.min()
        if op == "ts_max":
            return rolling.max()
        if op == "ts_rank":
            return rolling.rank(pct=True)
        if op == "ts_corr":
            return rolling.corr(args[1])
        raise invalid(f"尚未实现的算子：{op}")

    value = visit(node)
    if not isinstance(value, pd.DataFrame):
        raise invalid("因子结果必须是日期 × 股票的二维表。")
    return value.replace([np.inf, -np.inf], np.nan)
