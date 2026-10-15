import random
import re

from loop_research.catalog import SEED_FACTORS

# A 20-item cycle preserves the 25/25/15/15/20 initial proportions exactly.
SCHEDULE = [
    "mutation",
    "crossover",
    "mechanism",
    "random",
    "perturbation",
    "mutation",
    "crossover",
    "mechanism",
    "mutation",
    "crossover",
    "perturbation",
    "random",
    "mechanism",
    "mutation",
    "crossover",
    "perturbation",
    "random",
    "mechanism",
    "mutation",
    "crossover",
]


def propose_fixture(seed: int, index: int, parents: list[dict]) -> dict:
    """A deterministic local fixture, never a claim of a model-generated hypothesis."""
    rng = random.Random(seed * 1_000_003 + index)
    strategy = SCHEDULE[index % len(SCHEDULE)]
    pool = parents[-12:] or SEED_FACTORS
    parent = rng.choice(pool)
    expression = parent["expression"]
    mechanism = parent.get("mechanism", "momentum")
    parent_ids = [parent["id"]] if "id" in parent else []
    if strategy == "mutation":
        expression = f"{rng.choice(['cs_rank', 'neg', 'abs'])}({expression})"
    elif strategy == "crossover":
        other = rng.choice(SEED_FACTORS)
        expression = f"sub(cs_rank({expression}), cs_rank({other['expression']}))"
    elif strategy == "perturbation":
        expression = re.sub(
            r",\s*(2|3|5|10|20|40|60)\)",
            lambda _: f", {rng.choice([2, 3, 5, 10, 20, 40, 60])})",
            expression,
        )
    elif strategy == "random":
        field = rng.choice(["ret1", "gap", "intraday_return", "intraday_range", "rel_volume"])
        expression = (
            f"{rng.choice(['ts_mean', 'ts_std', 'ts_rank'])}({field}, {rng.choice([3, 5, 10, 20])})"
        )
        parent_ids = []
    elif strategy == "mechanism":
        expression = f"sub(ts_mean(gap, {rng.choice([3, 5, 10, 20])}), ts_mean(intraday_range, 10))"
        mechanism = "gap_range_interaction"
        parent_ids = []
    return {
        "name": f"候选 {index + 1:03d}",
        "expression": expression,
        "strategy": strategy,
        "mechanism": mechanism,
        "parent_ids": parent_ids,
        "hypothesis": "本地预置生成示例，用于检查任务流转；未经过模型审查或市场验证。",
        "origin": "fixture",
        "llm_review": "not_run",
    }
