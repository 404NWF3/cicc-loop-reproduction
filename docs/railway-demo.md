# Railway 网页研究版资源验证

2026-10-15，内置历史快照、14 页网页演示、图片与字体，并整合现有网站认证与部署配置后，在本地对生产镜像施加 **1GiB 内存硬上限、1 CPU**，运行一个 API 与一个真实研究 worker。

| 项目 | 最终镜像实测 |
| --- | ---: |
| cgroup 内存峰值 | **264.7MiB**（277,557,248 字节） |
| 未压缩最终镜像 | **252.12MB** |
| 生产 Python 环境 | 118.16MB |
| 完成任务后的数据库 / 可写层 | 10.72MB / 10.74MB |
| 候选处理 / 实际回测 | 1,200 / 366 |
| 本次入库 | 6 个归档种子复算，0 个新候选 |
| 并发读取客户端 | 4 |
| HTTP 读取次数 / 错误 | 27,144 / 0 |
| HTTP 响应 P95 | 0.051 秒 |
| 任务与并发读取总耗时 | 232.2 秒 |
| 分页核对 / 完整 JSON 导出 | 1,200 条无重复、无遗漏 / 8.73MB |
| OOM / OOM kill | 0 / 0 |
| DeepSeek 调用 | 0 |

精确测量及镜像 ID 见 [resource-profile-live.json](resource-profile-live.json)。内存硬上限实际为 1,073,741,824 字节；候选与并发读取均完整执行。

最终镜像不含 Node/npm、SciPy、notebook 工具、原始市场 CSV 或完整实验产物。压缩后的开发快照为 1.25MB，网站归档数据约 124KB，照片和字体约 2.6MB；没有 PPTX / PDF 文件和下载接口。运行时不下载市场数据。

500MB 文件系统配额未在本地强制模拟；表中分别测量未压缩镜像、应用和实际写入，平台计量以 Railway 为准。状态默认软上限 64MiB，包含 SQLite、WAL、SHM；超限后保存历史并停止新写入，不自动删除旧任务。

## 部署设置

沿用多阶段 `Dockerfile` 与 Railway 控制台配置，健康检查 `/api/v1/health`。`python -m loop_research.deploy` 读取 Railway 的 `PORT`，强制网站登录并检查持久卷，默认 BLAS/OMP 线程数为 1，API 最大并发连接数为 24。资源最省的方式是 API 同时提供静态前端。具体配置见 [部署说明](railway.md)。

已有前后端分开部署时，前端构建环境设置 `VITE_API_BASE_URL=https://后端域名`，后端设置 `LOOP_CORS_ORIGINS=https://前端域名`。前端变量变更需要重新构建；Docker 构建也接受同名参数。

继续将 Volume 挂载到 `/data`，运行数据库位于 `/data/runtime`，累计账本为 `/data/deepseek.sqlite3`。保持单实例和持久卷；迁移时一起迁移账本。镜像自动带入此前已发生的模型用量，不从零开始计费。

生产环境沿用 `LOOP_AUTH_USERNAME` / `LOOP_AUTH_PASSWORD`。登录后本地搜索免费；要使用网页 DeepSeek 模式，在后端设置 `DEEPSEEK_API_KEY` 和独立的 `LOOP_RESEARCH_TOKEN`。网页只提交演示口令，不能把 API Key 写入前端环境。模型任务创建与控制均检查口令。浏览、翻页和读取结果不触发模型请求。

当前版本在本地验证，线上状态以 Railway 部署记录为准。完整演示说明见 [web-research-demo.md](web-research-demo.md)。

## 本地复测

```bash
docker build -t loop-research:live .
uv run python scripts/profile_demo.py --image loop-research:live --mode live
```

生产 Dockerfile 使用普通依赖安装命令，保留 Railway 不支持 secret mount 的兼容修复。当前工作区在临时构建文件中通过 secret mount 为依赖安装挂载公开代理 CA，保持 TLS 校验；该临时文件和 CA 不提交，也不进入镜像层。GitHub CI 直接构建仓库中的 Dockerfile。

脚本不向容器传递 DeepSeek 凭据，真实执行 1,200 个候选的历史计算；并行运行四个读取客户端，结束后核对游标分页与完整 JSON 导出。完成后删除测试容器，保留统计 JSON。`--mode fixture` 仍可运行旧 1,000 候选的流程测试。

此前纯 fixture 版本的 209MiB 峰值与 248MB 镜像测量仍保存在 [resource-profile.json](resource-profile.json)，不作为当前真实计算版本的资源结论。
