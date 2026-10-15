"""Single-process production entry point used by the Docker image."""

import os
from pathlib import Path

import uvicorn
from pydantic import ValidationError

from loop_research.api import create_app
from loop_research.config import Settings


def validate_deployment(settings: Settings) -> int:
    try:
        port = int(os.environ.get("PORT", "8000"))
    except ValueError:
        raise ValueError("PORT 必须是 1–65535 的整数。") from None
    if not 1 <= port <= 65535:
        raise ValueError("PORT 必须是 1–65535 的整数。")
    if not (settings.web_dist / "index.html").is_file():
        raise ValueError("找不到前端构建产物；请使用完整 Docker 构建。")
    if not settings.worker_autostart:
        raise ValueError("单服务部署要求 LOOP_WORKER_AUTOSTART=true。")
    if os.environ.get("RAILWAY_SERVICE_ID"):
        mount = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
        if not mount:
            raise ValueError("请先为 Railway 服务挂载 /data 持久卷，再重新部署。")
        volume = Path(mount).resolve()
        if not volume.is_dir() or not all(
            path.resolve().is_relative_to(volume)
            for path in (settings.state_dir, settings.data_dir, settings.budget_path)
        ):
            raise ValueError(
                "LOOP_STATE_DIR、LOOP_DATA_DIR 和 LOOP_BUDGET_PATH 必须位于已挂载的持久卷内。"
            )
    return port


def main():
    try:
        # A container never silently starts an unauthenticated development server.
        settings = Settings(_env_file=None, auth_required=True)
        port = validate_deployment(settings)
    except ValidationError as exc:
        messages = [e["msg"] for e in exc.errors(include_input=False, include_context=False)]
        raise SystemExit("部署配置无效：" + "; ".join(messages)) from None
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    uvicorn.run(
        create_app(settings),
        host="0.0.0.0",
        port=port,
        workers=1,
        limit_concurrency=24,
        timeout_keep_alive=5,
        access_log=False,
        proxy_headers=True,
        forwarded_allow_ips="*",  # Railway terminates HTTPS at its ingress proxy.
        timeout_graceful_shutdown=10,
    )


if __name__ == "__main__":
    main()
