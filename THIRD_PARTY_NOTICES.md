# 第三方参考与依赖

引擎、后端与研究图表为本项目编写；网页演示模板来源另列于下。材料提供研究机制与目标，不构成对原机构内部代码或实际效果的验证。

## 研究参考

| 资料 | 许可 / 使用情况 |
| --- | --- |
| [Microsoft Qlib](https://github.com/microsoft/qlib) | MIT；已查看 Alpha158 定义，作为后续公式核对参考。本框架未复制其源码或安装其模型运行栈。 |
| [Microsoft RD-Agent](https://github.com/microsoft/RD-Agent) | MIT；工作流参考。未采用其智能体框架。 |
| [Alphalens Reloaded](https://github.com/stefan-jansen/alphalens-reloaded) | Apache-2.0；计划用于后续 IC 交叉核对，当前不属于运行依赖。 |
| [StockNet](https://github.com/yumoxu/stocknet-dataset) | 仓库 MIT，注明价格源为 Yahoo Finance；本地下载 commit `330708b5ddc359961078bef469f43f48992fd6e4` 的 88 个价格 CSV，按搜索期质量选取 50 股开展首轮实验。源文件、校验和、许可证链接保留在本地 manifest；网站展示派生汇总结果；演示服务同时内置仅含 2012–2015 年开发期的 50 股压缩快照。原仓库 MIT 声明保留在 `src/loop_research/demo/STOCKNET_LICENSE`，Yahoo 价格来源一并注明。 |
| 用户提供的中金案例分析 | 用于背景、策略初始配比、部分阈值和方法说明。网站注明独立复现与材料边界。 |

窗口动量、反转、滚动波动、相关系数等通用公式由本项目直接实现。后续若复制或改写第三方源码，需另行保留原版权声明、许可证及对应 commit。

## 软件依赖

Python 与 npm 的运行/开发依赖及精确版本记录于 `pyproject.toml`、`uv.lock`、`package.json` 和 `package-lock.json`。各依赖的许可随其软件包分发。Lucide 提供页面图标；页面没有使用中金官方标识。研究演示自托管 Noto Serif CJK SC 的字符子集，SIL Open Font License 原文见 `web/public/presentation/FONT-LICENSE.txt`。

SciPy（BSD-3-Clause）仅用于开发环境的独立 IC/费用求解核对，不进入生产镜像。Notebook 临时环境的 Matplotlib（Matplotlib license）用于绘制本地研究图表，不成为网站依赖。未将 Qlib、RD-Agent 或 Alphalens 源码复制进引擎；本轮直接以 SciPy 进行数值交叉检查，Alphalens 的原计划仍未执行。

## 网页研究演示图像

| 文件 | 作者与授权 | 原始出处 |
| --- | --- | --- |
| `shanghai.jpg` | King of Hearts，CC BY-SA 4.0 | [Pudong Shanghai November 2017 panorama](https://commons.wikimedia.org/wiki/File:Pudong_Shanghai_November_2017_panorama.jpg) |
| `trading-floor.jpg` | Carol M. Highsmith，公有领域 | [NYSE 历史交易大厅](https://commons.wikimedia.org/wiki/File:New_York_Stock_Exchange_trading_floor_on_Wall_Street,_New_York,_New_York_LCCN2011634218.tif) |
| `servers.jpg` | Unnerving duck，CC BY-SA 4.0 | [CERN GBAR 附近机柜](https://commons.wikimedia.org/wiki/File:Server_racks_near_the_GBAR_experiment.jpg) |

三张照片使用 Commons 提供的缩略文件，原文件不修改；页面通过 CSS 裁切显示。照片及其显示裁切部分遵循原授权，CC BY-SA 4.0 见 https://creativecommons.org/licenses/by-sa/4.0/ 。完整作者、授权、来源与缩略图 URL 在 `web/public/presentation/sources.json`，页面「资料」面板可直接查看。CERN 和 NYSE 图片仅作概念与背景配图，不代表中金内部设备或场景。

[R2D3](https://r2d3.us/visual-intro-to-machine-learning-part-1/) 仅作为用户指定的视觉叙事参考，未复制插图、文案或源代码。图表由本项目按注明来源重绘；本地 23 因子的配对图源于实际归档结果。

## 网页演示模板

研究演示采用 [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) 的 Style A，固定 commit `c91369c449d34755d320a8b81d0734000d99d1ab`，Copyright © 2026 op7418，AGPL-3.0。上游模板原样保存在 `web/presentation/template.html`；适配代码、研究布局与生成演示遵循同一许可。修改包括本地字体与图标、静态背景、研究内容、网站通信、键盘无障碍与手机阅读。完整许可保存在 `web/public/presentation/licenses/AGPL-3.0.txt`；当前部署的对应源码与许可从演示「资料」面板可查看，构建时生成到 `/presentation/source/`。不复制技能赞助信息到演示。
