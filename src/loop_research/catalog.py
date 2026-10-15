STRATEGIES = [
    {
        "id": "mutation",
        "name": "结构变异",
        "weight": 0.25,
        "description": "替换父代的局部结构，在已知机制附近寻找新表达。",
    },
    {
        "id": "crossover",
        "name": "因子交叉",
        "weight": 0.25,
        "description": "组合两个父代，探索信号之间的相互作用。",
    },
    {
        "id": "perturbation",
        "name": "参数扰动",
        "weight": 0.15,
        "description": "在相同结构中改变观察窗口，检查时间尺度。",
    },
    {
        "id": "random",
        "name": "随机探索",
        "weight": 0.15,
        "description": "从受限语法生成新候选，保持探索空间开放。",
    },
    {
        "id": "mechanism",
        "name": "机制引导",
        "weight": 0.20,
        "description": "根据机制覆盖提出假设；演示模式使用预置案例。",
    },
]

SEED_FACTORS = [
    {
        "name": "20 日动量",
        "expression": "sub(safe_div(close, delay(close, 20)), 1)",
        "mechanism": "momentum",
        "hypothesis": "检验中期价格趋势是否具有持续性。",
    },
    {
        "name": "5 日反转",
        "expression": "neg(sub(safe_div(close, delay(close, 5)), 1))",
        "mechanism": "reversal",
        "hypothesis": "检验短期价格偏离之后的均值回归。",
    },
    {
        "name": "低波动",
        "expression": "neg(ts_std(ret1, 20))",
        "mechanism": "volatility",
        "hypothesis": "比较不同股票近期波动的差异。",
    },
    {
        "name": "隔夜跳空",
        "expression": "ts_mean(gap, 5)",
        "mechanism": "overnight",
        "hypothesis": "观察连续隔夜溢价的积累。",
    },
    {
        "name": "日内压力",
        "expression": "ts_mean(intraday_return, 5)",
        "mechanism": "intraday",
        "hypothesis": "刻画日内买卖压力的持续方向。",
    },
    {
        "name": "价量关系",
        "expression": "neg(ts_corr(ret1, rel_volume, 20))",
        "mechanism": "volume_price",
        "hypothesis": "检验价格变化与相对成交量之间的背离。",
    },
]

MECHANISMS = [
    "momentum",
    "reversal",
    "overnight",
    "intraday",
    "range_change",
    "volume_price",
    "relative_volume",
    "volatility",
    "upper_shadow",
    "lower_shadow",
    "breakout",
    "trend_consistency",
    "gap_range_interaction",
]
