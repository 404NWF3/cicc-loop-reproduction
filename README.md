# Loop Research · 因子发现实验室

中金 Loop Engineering 因子发现流程的轻量复现工程。使用 **Python / FastAPI / SQLite + React / TypeScript / Vite**，通过 DeepSeek 官方 HTTP API 生成与审查候选，不依赖智能体开发框架。

**网页已整合实时挖掘与 14 页研究演示。** `/presentation` 支持全屏、目录、键盘翻页与讲稿，第 13 页进入 `/mine` 启动真实历史计算。按最新要求不提供 PPTX / PDF 下载入口。[演示流程与部署说明](docs/web-research-demo.md)。

**扩大实验已完成：6,637 次尝试、966 次完整回测，去相关后 23 个因子通过开发筛选入库。** 保留原 11 项门槛与交易成本。留出期仅 1 个因子年化超额为正，预先选定的前五组合年化超额 **−3.18%**，因此不能据此宣称稳定 Alpha。两轮累计 DeepSeek usage 估算约 **0.1325 元**，余额差额约 **0.13 元**，累计保守费用上界 **0.358688 元 / 40 元**。[扩大实验报告](docs/experiment-expanded-2026-10-15.md) 与[已执行 notebook](notebooks/stocknet-expanded-experiment.ipynb)保留全部结果。

[首轮报告](docs/experiment-2026-10-15.md)继续保留：50 股、306 次尝试、217 次回测，0 入库。网站可切换两轮结果，不覆盖失败记录。

网站 `/experiments` 读取精简归档结果；`/mine` 在固定历史开发快照上真实生成、回测和筛选。免费本地模式先复算 6 个归档种子，再探索新候选，分别计数。可选 DeepSeek 模式需要服务端口令和共享预算。旧控制台的 `fixture` 流程仍不产生回测收益。

网页真实模型验证新增 2 次调用、2,180 tokens。包括之前两轮实验，当前累计 **52 次请求、47,016 tokens、保守费用上界 0.376128 元 / 40 元**；历史实验报告中的费用保持当时的归档值。

完整目标与来源见 [SPEC.md](SPEC.md)，当前实现范围以下文为准。

## 快速启动

环境要求：Python 3.12+、uv、Node.js 22.12+（当前云环境为 Node 24）、npm。

在仓库根目录执行，云环境路径为 `/workspace/cicc-loop-reproduction`：

```bash
uv sync --frozen
npm ci
npm run dev
```

启动脚本会同时运行前端（端口 **5173**）、后端（端口 **8000**）及一个独立 worker。`Ctrl+C` 停止本次启动的进程。默认不需要 `.env` 或 API Key。

打开前端后，点击「研究演示」进行网页放映，或进入「实时挖掘」启动默认 1,200 个本地候选；短演示可选择 24 或 36 个。可选择 15/30/60 分钟时限，默认 60 分钟。DeepSeek 单次预算默认 5 元，可选 1/3/5/10 元；累计 40 元上限保持不变。可以观察候选、暂停、刷新后继续、停止、查看实际净值、11 项门槛和导出研究 JSON。旧控制台也保留公式结构校验与 fixture 流程。

后端提供 OpenAPI 文档，路径为 `/docs`；健康检查为 `/api/v1/health`。

### 分别启动与生产构建

```bash
# 终端 A：API 自动管理 worker
uv run loop-research serve

# 终端 B：Vite 开发服务
npm run dev:web

# 生产构建；完成后 API 会直接提供 web/dist 和 SPA 路由
npm run build
uv run loop-research serve
```

Vite 在开发环境代理 `/api` 到后端。可用 `LOOP_API_PROXY` 指定不同后端端口。后端支持 SPA 刷新；未知 API 路径仍返回 JSON 404。

前后端分开部署时，在前端构建环境设置 `VITE_API_BASE_URL=https://后端域名`，后端设置 `LOOP_CORS_ORIGINS=https://前端域名`。HTTP、SSE 和实验结果链接共用同一 API 地址。生产环境需先在后端域名完成登录；跨域认证及同域部署说明见 [Railway 部署](docs/railway.md)。单服务部署可省略这两个设置。

## 已实现的框架

| 部分 | 现在可用 |
| --- | --- |
| 展示网站 | 研究概览、交互原理页、版本切换、真实实验统计、全部入库因子的开发/留出对照 |
| 网页演示 | 14 页研究叙事、资料署名、逐页讲稿、全屏、目录与键盘翻页、手机阅读 |
| 现场挖掘 | 历史快照上的真实生成/回测/门槛，归档种子与新候选区分，口令保护的模型模式 |
| 控制台 | 任务创建、启动、暂停、恢复、停止、历史列表、候选详情、配置检查、JSON 导出 |
| 实时状态 | SSE、Last-Event-ID 补读、断线提示、轮询回退 |
| 持久化 | SQLite WAL、事务写入候选与检查点、创建幂等键、单活跃任务、worker lease |
| DSL | 受限 AST、量纲/复杂度/回看长度检查、历史时序与截面算子、禁止任意 Python 执行 |
| 候选与 FSA | 五种策略的固定初始配比、可重复演示生成、精确去重、频繁骨架窗口与冻结 |
| 数值模块 | t+1 开盘成交、周期调仓、漂移后换手、双边费用、缺失价格失败、IC 与相对绩效函数 |
| 联合过滤 | 11 项本地口径，未计算或非有限指标不会通过 |
| 数据契约 | 本地 CSV 注册、SHA-256、OHLCV/重复键检查、统一宽表转换 |
| 模型模块 | 官方 API 适配器、独立生成/审查提示词、结构化校验、请求/token 预算、有限重试 |
| 开发验证 | Python 测试、前端类型检查/构建、浏览器端到端测试、CI 配置 |

### 演示和真实运行的边界

- `fixture` 使用本地预置生成规则；机制引导也使用预置案例。LLM 审查显示「未运行」。
- 候选最多停留在「等待数据」状态。**结构合法不等于通过回测，更不等于正式入库。**
- 演示不会调用数值回测器，所有绩效值保持 `null`，11 项 gate 显示「尚未计算」。
- 控制台演示不产生市场实验结果；真实实验归档另在 `/experiments` 展示，并已做独立数值复核。
- `mode=live` 已接通独立研究 worker，真实重算开发期数据；最多 1,200 候选、3,600 秒，不加载留出期价格。
- `POST /models/check` 仅检查本地配置，明确返回 `remote_check_performed=false`。

完整实验 CLI 支持固定数据快照与复权、时间隔离、模型调用归档、五策略与动态调权、FSA、11 项筛选和冻结后的测试期评估。网页是有规模上限的开发期现场研究，支持任务控制与共享账本，不等于完整消融实验，也不构成新的独立样本外检验。

## 模型与运行配置

需要配置时，将 `.env.example` 复制为本地 `.env`；保留已有配置，不覆盖自己的密钥。

| 变量 | 默认值 / 作用 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 空；仅后端读取，不返回前端 |
| `DEEPSEEK_MODEL` | `deepseek-flash`；已核实的官方 ID |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com`；只接受官方 HTTPS 地址及其 `/v1` 路径 |
| `LOOP_STATE_DIR` | `./artifacts/runtime`，保存 SQLite |
| `LOOP_STATE_MAX_MB` | `64`，演示数据库及 WAL 的软上限；超限停止增长并保留历史读取 |
| `LOOP_DATA_DIR` | `./data`，保存本地数据快照 |
| `LOOP_WORKER_AUTOSTART` | `true`，API 启动独立 worker |
| `LOOP_FIXTURE_STEP_SECONDS` | `0.3`，演示候选之间的间隔 |
| `LOOP_WEB_DIST` | `./web/dist`，生产前端目录 |
| `LOOP_LIVE_ENABLED` | `true`，启用历史快照现场研究 |
| `LOOP_RESEARCH_TOKEN` | 空；设置后配合服务端 Key 开启付费模式，浏览器只提交演示口令 |
| `LOOP_BUDGET_PATH` | 本地共享 `artifacts/budgets/deepseek.sqlite3`；Docker 为 `/data/deepseek.sqlite3` |
| `LOOP_AUTH_USERNAME` / `LOOP_AUTH_PASSWORD` | 本地可选；生产必须配置，密码至少 16 字符，保护页面、API 和 SSE |
| `LOOP_CORS_ORIGINS` | 空；分开部署时指定前端精确来源，逗号分隔 |
| `VITE_API_BASE_URL` | 空；前端构建时指定独立后端域名，默认同源 |

2026-10-15 已通过官方 `/models` 与官方定价页核实，**DeepSeek-V4.1-Flash** 对应 `deepseek-flash`。本地实验与网页模型模式固定使用该型号，关闭思考模式。浏览和本地搜索不会调用模型；DeepSeek 任务需要正确演示口令后显式创建、启动。

模型连接超时后的结果可能未知，客户端会保留预算且不静默重发；429 和部分 5xx 最多重试两次。本地实验共享 `artifacts/budgets/deepseek.sqlite3`，发送前用 SQLite 事务预留请求、token 与人民币费用；缺少 usage 或网络结果未知时不释放预留。所有 token 均按官方高峰输出价 8 元/百万计入保守上界。网页任务同时受单次预算和累计 40 元限制，请求/token 次级上限为 2,000 次 / 500 万。首次升级只将旧版默认的 60 次 / 12 万 token 迁移到新上限；历史用量、未知预留与人民币上限保留，更严格的自定义限制不会被抬高。原归档实验协议仍保留其 60 次 / 12 万 token 设置。账本重启后保留，已有额度不能通过新建实验目录重置。

DeepSeek 每批最多生成 12 个候选，再由独立上下文审查，随后真实回测。下一批收到开发期失败原因、近期公式与前三个开发期候选作为反馈，直到候选、时间或预算任一上限到达；不再只生成最初一批后转为本地搜索。每批原始响应单独归档，检查点只保留当前批次，刷新恢复不会重新支付已完成的请求。

本项目是共享课堂演示空间，无多租户私密数据隔离。生产入口沿用网站登录保护，付费任务的创建和全部控制额外要求服务端演示口令；本地任务受单活跃任务、CPU 时间与存储限制。CLI 默认只绑定回环地址，公开监听也必须配置账号密码。

## CLI 与数据契约

```bash
# 离线诊断，不发起模型请求
uv run loop-research doctor --offline

# 先启动 serve，再排入一个演示任务
uv run loop-research run --config configs/smoke.yaml

# 可选：关闭 API 自动 worker 后手工启动（不要改变运行任务的数据库路径）
uv run loop-research worker

# 后续有自己的数据时，显式注册本地 CSV；这不会运行回测
uv run loop-research data register --csv /path/to/prices.csv --id my-dataset
uv run loop-research data validate my-dataset
```

CSV 必需列：`date,symbol,open,high,low,close,volume`。记录以 `(date,symbol)` 唯一，价格正数，成交量非负，高低价关系成立。注册使用新目录，不覆盖已存在的数据集。

目前注册校验只证明结构和价格关系成立，不能证明复权或历史可得性正确。原始文件、SQLite、测试截图和环境配置都在 `.gitignore` 中。

worker 正常关闭或租约失效后，正在执行的任务变成 `interrupted`，可从控制台继续。候选和游标在同一事务中提交；恢复不重复计数。候选预算与墙钟预算达到上限时状态为 `budget_exhausted`，其中墙钟时间包含暂停时间。

## 目录

```text
src/loop_research/
  api.py                 FastAPI、SSE、开发控制 API、生产静态页面
  storage.py             SQLite、事务、worker 租约与状态转换
  worker.py              独立进程入口
  live.py                有限规模的历史现场研究与模型检查点
  demo/                  1.25MB 开发快照、来源清单、历史预算基线
  cli.py                 诊断、服务、演示和数据命令
  factors/               DSL、演示生成、FSA
  backtest/              自融资回测、指标与 gate 纯函数
  data/                  本地 CSV 注册与校验
  models/                官方客户端、结构化生成与审查服务
  prompts/               生成与审查提示词
  loop/runner.py         演示与真实研究循环分发
web/src/
  pages/                 研究页面与控制台
  presentation/          14 页演示文稿数据与样式
  api.ts                 类型化 API 客户端
  hooks.ts               查询、事件流与连接状态
  components.tsx         通用组件
  styles.css             设计变量与响应式布局
tests/                   Python 单元与接口测试
web/e2e/                 真实浏览器与后端的集成测试
configs/smoke.yaml        演示任务配置
```

### 本地真实实验与免费回放

扩大实验的固定协议在 `src/loop_research/experiments/expanded.py`，沿用同一个累计预算账本：

```bash
uv run python -m loop_research.experiments.expanded --id my-expanded-experiment
uv run python -m loop_research.experiments.expanded --id my-expanded-replay \
  --replay artifacts/stocknet_flash_20261015_v2
uv run python scripts/verify_expanded.py artifacts/stocknet_flash_20261015_v2
```

首轮小规模协议及通用导出命令：

```bash
# 自动取得固定 commit 的 StockNet 原始 CSV；真实调用共享 40 元预算账本
uv run loop-research experiment --id my-local-experiment

# 对已归档的模型响应精确回放；不会请求 DeepSeek
uv run loop-research experiment --id my-replay \
  --replay artifacts/stocknet_flash_20261015_v1

# 独立数值复核；SciPy 只在 dev 依赖中
uv run python scripts/verify_experiment.py artifacts/stocknet_flash_20261015_v1

# 仅把已完成且通过数值复核的精简结果加入网站
uv run python scripts/export_experiment.py artifacts/stocknet_flash_20261015_v1

# 可选 notebook 工具通过临时环境安装，不进入生产镜像
uv run --with nbformat --with nbclient --with ipykernel --with matplotlib --with nbconvert \
  python scripts/build_experiment_notebook.py
```

配置在 `configs/local_experiment.yaml`，运行前即固化；不支持通过编辑成本、日期或门槛而悄悄改变当前协议。现有实验 ID 不会覆盖或重新扣费。原始 CSV、所有候选、IC/日收益、模型调用、冻结清单、源代码快照和预算保存在本地 `data/`、`artifacts/`，不随网站部署。正式实验的 checkpoint 暂不支持断点恢复；中断时保留部分结果，使用新 ID 显式回放，不能把部分实验称为完整结果。

`SPEC.md` 保留完整系统设计基线；网页现场研究只实现本文说明的有界子集。已有命令以 `uv run loop-research --help` 为准。

## Railway：1GB 内存、500MB 存储

使用仓库的多阶段 `Dockerfile` 和 Railway 控制台设置，完整步骤见 [部署文档](docs/railway.md)。Node 仅在构建阶段编译静态前端；生产环境运行一个 API 进程与一个研究 worker，无开发服务器、无 SciPy、无启动时数据下载。默认本地搜索免费。启动入口读取 Railway 的 `PORT`，要求登录凭据、前端构建产物及持久卷。也可以保留现有前后端服务，按上文设置 API 地址和精确 CORS 来源。

状态默认限制为 64MiB（数据库、WAL、SHM 合计的软上限），超限后阻止创建新任务并在检查点停止候选写入；保留历史，不自动删除。继续将 Railway Volume 挂载到 `/data`，任务保存在 `/data/runtime`，累计费用账本保存在 `/data/deepseek.sqlite3`。原始市场数据和完整实验产物留在本地，镜像仅加入约 1.25MB 开发快照、124KB 归档结果及约 2.6MB 照片/字体。本地模式无需配置 Key。

[最新实测资源记录](docs/railway-demo.md)：1GiB 内存硬限下完成 1,200 个真实候选处理及四并发读取，内存峰值约 **264.7MiB**、最终镜像约 **252MB**、数据库约 **10.72MB**，无 OOM 或 HTTP 错误；完整任务约 232 秒。500MB 文件系统配额未在本地强制模拟，实际存储以 Railway 计量为准。

```bash
docker build -t loop-research:railway .
uv run python scripts/profile_demo.py --image loop-research:railway --mode live
```

已有历史预算会带入新的持久账本。使用单实例并保留持久卷；迁移时一并迁移账本，避免重置累计用量。每个网页付费任务默认上限 5 元，最多 10 元；预算是停止上限，不会预先扣除或为了用尽预算而增加调用。

## 验证

```bash
uv run ruff check src tests
uv run pytest
npm run build
npm run test:e2e
```

浏览器测试使用独立的临时数据库，自动启动端口 8001/5174 的测试服务。优先使用 `/usr/bin/chromium`；本机没有浏览器时，先运行 `npm exec --workspace web -- playwright install chromium`，或通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 指定已有浏览器。

测试覆盖未来数据隔离、手算成交与费用、未知指标、FSA、任务中断恢复、单 worker 限制、模型接口模拟响应、数据校验和、网站与付费口令认证、跨域请求、持久卷路径、浏览器中的真实任务控制及移动端布局。容器冒烟还覆盖动态端口、SSE、正常关闭与容器替换后的状态恢复。测试不连接 DeepSeek，不下载金融数据。

可用 `npm run format` 整理前端格式；Python 使用 `uv run ruff format src tests`。依赖由 `uv.lock` 与 `package-lock.json` 固定。
