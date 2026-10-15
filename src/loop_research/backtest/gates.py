import math

GATES = [
    ("G01", "Rank IC 绝对值", "abs_ic", ">", 0.03, "discovery", "material_adapted"),
    ("G02", "筛选第一年超额", "year1_excess", ">", 0, "selection", "material_adapted"),
    ("G03", "筛选第二年超额", "year2_excess", ">", 0, "selection", "material_adapted"),
    ("G04", "筛选第一年夏普", "year1_sharpe", ">", 0.5, "selection", "material_adapted"),
    ("G05", "筛选第二年夏普", "year2_sharpe", ">", 0.5, "selection", "material_adapted"),
    ("G06", "Calmar 比率", "calmar", ">", 1, "selection", "material_adapted"),
    ("G07", "近 9 月超额", "last9m_excess", ">", 0, "selection", "material_adapted"),
    ("G08", "近 12 月超额", "last12m_excess", ">", 0, "selection", "material_adapted"),
    ("G09", "最大因子相关", "max_correlation", "<", 0.7, "selection", "material_adapted"),
    ("G10", "有效覆盖率", "coverage", ">=", 0.9, "development", "local_reconstruction"),
    ("G11", "样本量检查", "sample_check", "==", 1, "development", "local_reconstruction"),
]


def evaluate_gates(metrics: dict) -> list[dict]:
    results = []
    for gate_id, name, key, op, threshold, period, origin in GATES:
        value = metrics.get(key)
        valid = isinstance(value, (int, float)) and math.isfinite(value)
        passed = False
        if valid:
            passed = {
                ">": value > threshold,
                "<": value < threshold,
                ">=": value >= threshold,
                "==": value == threshold,
            }[op]
        results.append(
            {
                "id": gate_id,
                "name": name,
                "key": key,
                "operator": op,
                "threshold": threshold,
                "value": value if valid else None,
                "status": ("passed" if passed else "failed") if valid else "not_evaluated",
                "period": period,
                "origin": origin,
            }
        )
    return results
