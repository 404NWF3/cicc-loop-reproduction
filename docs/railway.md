# Railway 部署

部署形态为一个 Docker 服务、一个 `/data` 持久卷。镜像内先构建 React 前端，再安装 Python 依赖；运行时 FastAPI 同时提供页面和 API，并管理一个独立 worker。当前仍是演示框架，不运行真实模型或市场实验。

## 1. 从 GitHub 创建服务

1. 使用 GitHub 仓库的 `main` 分支，并先合并所需的部署修复。
2. 在 Railway 新建项目，选择 **Deploy from GitHub repo**，授权并选择 `404NWF3/cicc-loop-reproduction`。
3. 服务的 Root Directory 使用仓库根目录，不要设置为 `web`。Railway 自动识别根目录的 `Dockerfile`；镜像构建包含前后端，不需要另建前端服务。
4. 保持 Build Command 和 Start Command 为空，使用 Dockerfile。镜像默认启动 `python -m loop_research.deploy`。

第一次自动部署如果先于变量和持久卷配置，会按设计退出；完成下面两步后重新 Deploy 即可。

## 2. 设置登录凭据

在服务 **Variables** 中设置：

| 变量 | 设置方式 |
| --- | --- |
| `LOOP_AUTH_USERNAME` | 自定账号，例如 `research`；不能包含空白或冒号 |
| `LOOP_AUTH_PASSWORD` | 唯一的随机密码，至少 16 个字符；作为敏感变量保存 |

可以在自己的终端用 `openssl rand -hex 24` 生成密码。不要把密码放入仓库、Dockerfile、构建参数或前端变量。

首次访问网站时，浏览器会弹出 HTTP Basic 登录框。登录后页面、API、导出和 SSE 使用同一凭据。只有 `GET /api/v1/health` 不需要登录。生产入口始终要求认证，设置 `LOOP_AUTH_REQUIRED=false` 也不会关闭它。

演示不需要 `DEEPSEEK_API_KEY`。以后如需使用模型适配器，在 Railway 另设密钥和核实过的 `DEEPSEEK_MODEL`；配置这些变量不会自动启用尚未实现的 live 流程。

## 3. 挂载持久卷

在项目画布添加 **Volume**，连接到此服务，将 **Mount Path** 设置为 `/data`。初期可按实际需要选择小容量，后续扩容。

以下路径已设置在 Docker 镜像中，通常不需要重复填写：

| 变量 | 镜像默认值 | 用途 |
| --- | --- | --- |
| `LOOP_STATE_DIR` | `/data/runtime` | SQLite 数据库、WAL 与检查点 |
| `LOOP_DATA_DIR` | `/data/datasets` | 本地数据快照 |
| `LOOP_WEB_DIST` | `/app/web/dist` | 构建好的前端 |
| `LOOP_WORKER_AUTOSTART` | `true` | 启动独立 worker |

不要将卷挂到 `/app`，否则会遮住镜像内的应用文件。Railway 自动注入 `RAILWAY_VOLUME_MOUNT_PATH`，不要手工伪造该变量。生产入口在检测到 Railway 环境时，会要求挂载卷，并检查两个数据目录都位于该卷内。

镜像使用 root 运行以兼容 Railway 的 root 所有持久卷，无需额外设置 `RAILWAY_RUN_UID`。卷仅在运行时挂载，因此初始化数据库在服务启动时完成。

## 4. 配置部署并生成链接

| Railway 设置 | 值 |
| --- | --- |
| Replicas | `1`；只使用一个区域 |
| Serverless / App Sleeping | 关闭，worker 需要持续运行 |
| Healthcheck Path | `/api/v1/health` |
| Healthcheck Timeout | `120` 秒 |
| Restart Policy | On Failure，按需要设置重试次数，例如 `10` |

不要增加 Uvicorn workers 或另建共享 SQLite 的 worker 服务。当前数据库和 worker lease 使用单实例本地存储。

重新 Deploy，等待健康检查成功。在 **Settings → Networking → Generate Domain** 生成 Railway HTTPS 地址。程序监听 `0.0.0.0:$PORT`，`PORT` 使用 Railway 注入的值；本地未设置时使用 `8000`。域名的目标端口应与该值一致。

Railway 入口终止 HTTPS；容器只接收代理后的 HTTP，并信任入口代理的转发头。公开访问使用 Railway 生成的 HTTPS 地址。

## 5. 验证与后续更新

1. 访问 `https://你的域名/api/v1/health`，应返回 `status: ok`、`worker: online`。worker 未取得租约时返回 503。
2. 打开首页，输入账号密码；进入研究控制台，新建演示任务，验证候选更新、暂停和恢复。
3. 重启或重新部署服务，确认历史任务仍然存在。被中断的任务需要从控制台继续；不会自动启动新的模型请求。
4. 后续推送到绑定分支可触发 Railway 自动部署。服务有持久卷时，替换实例会有短暂中断。

Railway 的健康检查用于部署阶段，不是持续运行监控。保留持久卷并按需要启用 Railway 卷备份；删除卷会删除研究记录。修改登录密码后，浏览器保存的旧凭据可能需要在新的无痕窗口中重新输入。

## Dockerfile 校验失败排查

若部署显示 **The Dockerfile failed validation**，打开 **View logs** 查看具体错误。Railway 的 Dockerfile 构建不支持 `RUN --mount=type=secret`，即使挂载是可选的也会拒绝；本仓库的生产 Dockerfile 使用普通依赖安装命令。

如果日志仍出现 `--mount=type=secret,id=proxy_ca`，说明部署使用了旧版本 Dockerfile。合并修复后，部署所选分支的最新提交，并检查部署记录中的提交是否已更新；同时确认 Root Directory 为仓库根目录，Build Command 和 Start Command 留空。

## 本地复现同一个镜像

```bash
cp .env.production.example .env.production
# 编辑 .env.production，填写自己的账号和随机密码
docker compose --env-file .env.production up --build -d
```

打开 `http://localhost:8000`。Compose 只把端口绑定到本机，使用具名卷保存数据。`docker compose --env-file .env.production down` 停止服务并保留卷；不要为保留数据的环境加 `-v`。

完整容器冒烟测试使用随机测试凭据和专用临时卷，验证拒绝匿名访问、动态端口、前端、任务执行、SSE、正常关闭以及容器替换后数据保留：

```bash
docker build -t loop-research:smoke .
python3 scripts/smoke_container.py --image loop-research:smoke
```

## 配置依据

本项目使用 Railway 自动识别 Dockerfile 和控制台设置。Railway 当前已将旧 `railway.json` / `railway.toml` 标记为弃用，且新服务不能启用旧配置；因此仓库没有添加这些文件。若将来需要集中管理多个服务，可另行引入 Railway IaC。

- [Dockerfile 构建](https://docs.railway.com/builds/dockerfiles)
- [Railway 对 Dockerfile secret mount 的支持说明](https://station.railway.com/questions/does-railway-support-run-mount-type-se-aa6a8782)
- [持久卷与权限](https://docs.railway.com/volumes)
- [部署健康检查](https://docs.railway.com/deployments/healthchecks)
- [Infrastructure as Code 与旧配置迁移](https://docs.railway.com/infrastructure-as-code)
