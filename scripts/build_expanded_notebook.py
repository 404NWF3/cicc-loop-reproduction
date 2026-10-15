"""Render archived expansion results; never calls a model or reruns the search."""

import sys
from pathlib import Path

import nbformat as nbf
from jupyter_client import KernelManager
from nbclient import NotebookClient
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
notebook = nbf.v4.new_notebook(
    cells=[
        md("""# StockNet 扩大实验：从候选数量到独立因子

本 notebook 只读取 `stocknet_flash_20261015_v2` 的归档，不调用模型。

这是一项在首轮零入库诊断后开展的**探索性扩展**。固定 50 股、原 11 项门槛、单边 0.1% 成本、5 日调仓与时间切分。E4 系统枚举；E5 三个种子各 1,000 次组合；E6 模型假设及局部变体；E7 按开发筛选期反馈进行三轮各 800 次搜索。不中途因成功而提前结束。

发现期：2012-09-04–2013-12-31；开发筛选期：2014–2015；留出期：2016-01-01–2017-09-01。方向只由发现期确定。先按发现期 IC 过滤，再回测开发筛选期；最终按开发夏普排序，以平均绝对截面秩相关 <0.7 去相关。全部入库因子冻结后才统一读取留出期表现；主组合固定使用排名前五个（不足五个则全部）。

扩大搜索增加过拟合风险。源股票池有幸存者/事后选样偏差，历史复权不是 point-in-time 数据；本结果不证明可交易 Alpha，也不能证明模型或 FSA 的因果贡献。
"""),
        code("""from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path.cwd()
EXPERIMENT = ROOT / 'artifacts/stocknet_flash_20261015_v2'
REPORT = json.loads((EXPERIMENT / 'report.json').read_text())
AUDIT = json.loads((EXPERIMENT / 'verification.json').read_text())
FIGURES = EXPERIMENT / 'figures'
FIGURES.mkdir(exist_ok=True)
assert REPORT['status'] == 'completed' and AUDIT['status'] == 'passed'
assert REPORT['budget']['cost_upper_bound_cny'] <= 40
plt.rcParams.update({'figure.dpi': 130, 'font.size': 10,
                    'axes.spines.top': False, 'axes.spines.right': False,
                    'savefig.facecolor': 'white'})
counts = pd.DataFrame(REPORT['branches']).T
display(counts[['attempts', 'legal', 'backtested', 'quality_passed', 'accepted']])
print('Total attempts:', counts.attempts.sum())
print('Full selection backtests:', counts.backtested.sum())
print('Before correlation screen:', counts.quality_passed.sum())
print('Final admitted library:', counts.accepted.sum())
"""),
        md("""## 全部尝试与最终入库

合法但重复、退化、发现期 IC 不足的表达式都留在尝试总数中。通过数值门槛的参数变体不等于不同因子；右图显示去相关后的数量。各分支规模和角色不同，共享候选库，不能据此作等预算优劣比较。
"""),
        code("""fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout='constrained')
for ax, keys, title in [
    (axes[0], ['attempts', 'backtested'], 'Attempt accounting'),
    (axes[1], ['quality_passed', 'accepted'], 'Before and after correlation screen')]:
    x = np.arange(len(counts))
    for j, key in enumerate(keys):
        bars = ax.bar(x + (j - .5) * .36, counts[key].astype(int), width=.34,
                      color=['#adbac7', '#173c52'][j], label=key.replace('_', ' '))
        ax.bar_label(bars, padding=3, fontsize=9)
    ax.set(xticks=x, xticklabels=counts.index, ylabel='Candidate count', title=title)
    ax.margins(y=.22)
    ax.legend(frameon=False, loc='upper left')
fig.savefig(FIGURES / 'expanded-accounting.png', bbox_inches='tight')
plt.show()
"""),
        md("""## 开发筛选期与留出期

以下逐个展示所有入库因子，包括留出期收益为负的结果。两段时间的长度不同，年化超额采用相同口径；开发数据参与了大量搜索，不是样本外业绩。所有策略与等权基准均扣费，并在区间结束时平仓。
"""),
        code("""rows = []
test = {f['id']: f for f in REPORT['holdout']['LIBRARY']['factors']}
for f in REPORT['accepted_factors']:
    rows.append({'Factor': f['id'], 'Expression': f['expression'], 'Direction': f['direction'],
                 'Discovery IC': f['discovery_ic'], 'Selection Calmar': f['metrics']['calmar'],
                 'Selection annual excess': f['periods']['selection']['annual_excess'],
                 'Holdout annual excess': test[f['id']]['annual_excess'],
                 'Holdout Sharpe': test[f['id']]['sharpe']})
factors = pd.DataFrame(rows)
display(factors)
factors.to_csv(EXPERIMENT / 'accepted-factors.csv', index=False)
fig, ax = plt.subplots(figsize=(10, max(4.5, len(factors) * .65)), layout='constrained')
y = np.arange(len(factors))
for j, key, color in [(0, 'Selection annual excess', '#adbac7'),
                      (1, 'Holdout annual excess', '#173c52')]:
    values = factors[key].to_numpy() * 100
    bars = ax.barh(y + (j - .5) * .36, values, height=.32, label=key, color=color)
    ax.bar_label(bars, labels=[f'{v:+.2f}%' for v in values], padding=5, fontsize=9)
ax.set(yticks=y, yticklabels=factors.Factor, xlabel='Annual relative return (%)',
       title='All admitted factors: development selection vs frozen holdout')
ax.invert_yaxis()
ax.axvline(0, linewidth=.8, color='#808b97')
ax.xaxis.set_major_formatter(PercentFormatter(100))
ax.margins(x=.22, y=.15)
ax.legend(frameon=False)
fig.savefig(FIGURES / 'selection-vs-holdout.png', bbox_inches='tight')
plt.show()
display(pd.DataFrame([REPORT['holdout']['TOP5']['composite']], index=['Frozen top-five rank blend']))
"""),
        md("""## 费用与独立复核

账本跨实验共用，重试及未知结果保留预留额，40 元为累计上限。保守费用将所有 token 均按最高输出单价计算。usage 高峰价估算与账户余额差额另存 `billing.json`；后者精度为分，可能受账户其他活动影响。

独立 SciPy Spearman 与标量持仓账本/Brent 费用求解器已检查六个基线及全部入库因子：发现期 IC、开发和留出净值、门槛、去相关与组合。完整代码快照、数据 hash、冻结清单和逐条失败结果保存在实验目录。
"""),
        code("""display(pd.DataFrame([REPORT['budget']]))
display(pd.DataFrame([{k: AUDIT[k] for k in [
    'accepted_count', 'max_ic_absolute_error', 'max_nav_absolute_error',
    'max_metric_absolute_error', 'max_correlation_absolute_error',
    'peak_price_usage_estimate_cny', 'tokens']}]))
assert sum(b['accepted'] for b in REPORT['branches'].values()) == len(rows)
assert AUDIT['max_ic_absolute_error'] < 1e-10
assert AUDIT['max_nav_absolute_error'] < 1e-10
print('Freeze SHA-256:', REPORT['freeze_sha256'])
print('Protocol SHA-256:', REPORT['protocol_sha256'])
"""),
    ]
)
notebook.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": sys.version.split()[0]},
}
nbf.validate(notebook)
manager = KernelManager(kernel_name="python3")
manager.kernel_spec.argv[0] = sys.executable
NotebookClient(
    notebook, km=manager, timeout=120, resources={"metadata": {"path": str(ROOT)}}
).execute()
path = ROOT / "notebooks/stocknet-expanded-experiment.ipynb"
nbf.write(notebook, path)
body, _ = HTMLExporter().from_notebook_node(notebook)
(ROOT / "artifacts/stocknet_flash_20261015_v2/notebook.html").write_text(body)
print(path)
