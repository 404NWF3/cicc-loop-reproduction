# 第三方参考与依赖

本次提交的引擎、后端与页面代码为本项目新写。材料提供研究机制与目标，不构成对原机构内部代码或实际效果的验证。

## 研究参考

| 资料 | 许可 / 使用情况 |
| --- | --- |
| [Microsoft Qlib](https://github.com/microsoft/qlib) | MIT；已查看 Alpha158 定义，作为后续公式核对参考。本框架未复制其源码或安装其模型运行栈。 |
| [Microsoft RD-Agent](https://github.com/microsoft/RD-Agent) | MIT；工作流参考。未采用其智能体框架。 |
| [Alphalens Reloaded](https://github.com/stefan-jansen/alphalens-reloaded) | Apache-2.0；计划用于后续 IC 交叉核对，当前不属于运行依赖。 |
| [StockNet](https://github.com/yumoxu/stocknet-dataset) | 仓库 MIT，价格来自其注明的数据来源；本轮没有下载完整数据或开展实验。 |
| 用户提供的中金案例分析 | 用于背景、策略初始配比、部分阈值和方法说明。网站注明独立复现与材料边界。 |

窗口动量、反转、滚动波动、相关系数等通用公式由本项目直接实现。后续若复制或改写第三方源码，需另行保留原版权声明、许可证及对应 commit。

## 软件依赖

Python 与 npm 的运行/开发依赖及精确版本记录于 `pyproject.toml`、`uv.lock`、`package.json` 和 `package-lock.json`。各依赖的许可随其软件包分发。Lucide 提供页面图标；页面没有使用中金官方标识或外部字体资源。
