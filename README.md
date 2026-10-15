# Loop Research · 因子发现实验室

中金 Loop Engineering 因子发现流程的轻量复现工程。使用 **Python / FastAPI / SQLite + React / TypeScript / Vite**，通过 DeepSeek 官方 HTTP API 预留生成与审查能力，不依赖智能体开发框架。

**当前交付是可运行的前后端框架，未开展市场实验。** 默认演示模式只生成候选表达式、执行规则检查并保存任务状态，不下载市场数据、不发送真实模型请求、不产生回测收益。

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

打开前端后，进入「研究控制台 → 新建演示任务」。可以观察候选、暂停、继续、停止、查看公式解析与导出演示 JSON。公式工作台可以单独检查 DSL。

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

### Railway / Docker 部署

仓库包含多阶段 `Dockerfile`、本地 `compose.yaml` 和容器冒烟测试。一个容器运行前端、API 和独立 worker，SQLite 与数据快照保存到 `/data` 持久卷。

在 Railway 导入 GitHub 仓库，设置 `LOOP_AUTH_USERNAME` 和至少 16 字符的 `LOOP_AUTH_PASSWORD`，挂载 `/data`，并将健康检查设为 `/api/v1/health`。生产入口自动读取 `PORT`，要求登录凭据和 Railway 持久卷，并保持单实例运行。

完整设置、获取 HTTPS 链接及本地 Docker 验证步骤见 [Railway 部署说明](docs/railway.md)。

## 已实现的框架

| 部分 | 现在可用 |
| --- | --- |
| 展示网站 | 深蓝/金色的研究概览、交互原理页、策略配比、来源说明、实验空状态 |
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
- 数值函数已用人工构造的小表验证；这不是公开市场数据实验或收益验证。
- `mode=live` 目前不能启动，返回 `live_pipeline_pending`；不会悄悄降级成演示。
- `POST /models/check` 仅检查本地配置，明确返回 `remote_check_performed=false`。

后续接入点：真实数据快照与复权处理、discovery/selection/holdout 协议、模型调用记录和预算持久化、动态策略调权、真正的联合筛选/因子库、实验组冻结及最终评估。当前没有报告 E0–E3 的结果。

## 模型与运行配置

需要配置时，将 `.env.example` 复制为本地 `.env`；保留已有配置，不覆盖自己的密钥。

| 变量 | 默认值 / 作用 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 空；仅后端读取，不返回前端 |
| `DEEPSEEK_MODEL` | 空；必须填写核实后的官方 ID |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com`；只接受官方 HTTPS 地址及其 `/v1` 路径 |
| `LOOP_STATE_DIR` | `./artifacts/runtime`，保存 SQLite |
| `LOOP_DATA_DIR` | `./data`，保存本地数据快照 |
| `LOOP_WORKER_AUTOSTART` | `true`，API 启动独立 worker |
| `LOOP_FIXTURE_STEP_SECONDS` | `0.3`，演示候选之间的间隔 |
| `LOOP_WEB_DIST` | `./web/dist`，生产前端目录 |
| `LOOP_AUTH_USERNAME` | 本地默认空；部署后的登录账号 |
| `LOOP_AUTH_PASSWORD` | 本地默认空；部署后的登录密码，至少 16 个字符 |
| `LOOP_AUTH_REQUIRED` | 本地默认 `false`；容器生产入口始终强制认证 |

用户指定的 **DeepSeek 4.1 Flash** 尚未核实官方模型 ID，因此没有猜测或硬编码型号。配置密钥也不会自动启用真实任务。`FactorAssistant` 与 `DeepSeekClient` 供下一阶段显式接入，当前 worker 不调用它们。

模型连接超时后的结果可能未知，客户端会保留预算且不静默重发；429 和部分 5xx 最多重试两次。目前该预算是独立客户端的内存状态，真实任务接入时需与持久化账本整合。

本项目采用单用户访问方式。CLI 默认只绑定回环地址；配置账号密码后才允许通过 CLI 绑定其他地址。Docker 生产入口保护页面、API 与 SSE，使用浏览器 HTTP Basic 登录，并通过 Railway HTTPS 入口访问。

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
  cli.py                 诊断、服务、演示和数据命令
  factors/               DSL、演示生成、FSA
  backtest/              自融资回测、指标与 gate 纯函数
  data/                  本地 CSV 注册与校验
  models/                官方客户端、结构化生成与审查服务
  prompts/               生成与审查提示词
  loop/runner.py         可恢复的演示循环
web/src/
  pages/                 研究页面与控制台
  api.ts                 类型化 API 客户端
  hooks.ts               查询、事件流与连接状态
  components.tsx         通用组件
  styles.css             设计变量与响应式布局
tests/                   Python 单元与接口测试
web/e2e/                 真实浏览器与后端的集成测试
configs/smoke.yaml        演示任务配置
```

`SPEC.md` 是后续完整研究系统的设计基线，部分拟实现命令（例如自动数据下载、完整小实验脚本）当前还未提供。已有命令以 `uv run loop-research --help` 为准。

## 验证

```bash
uv run ruff check src tests scripts/smoke_container.py
uv run pytest
npm run build
npm run test:e2e
```

浏览器测试使用独立的临时数据库，自动启动端口 8001/5174 的测试服务。优先使用 `/usr/bin/chromium`；本机没有浏览器时，先运行 `npm exec --workspace web -- playwright install chromium`，或通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 指定已有浏览器。

测试覆盖未来数据隔离、手算成交与费用、未知指标、FSA、任务中断恢复、单 worker 限制、模型接口模拟响应、数据校验和、浏览器中的真实任务控制及移动端布局。测试不连接 DeepSeek，不下载金融数据。

可用 `npm run format` 整理前端格式；Python 使用 `uv run ruff format src tests`。依赖由 `uv.lock` 与 `package-lock.json` 固定。
