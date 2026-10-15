import asyncio
import json
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException

from loop_research import __version__
from loop_research.auth import authenticated
from loop_research.backtest.gates import evaluate_gates
from loop_research.catalog import MECHANISMS, SEED_FACTORS, STRATEGIES
from loop_research.config import Settings
from loop_research.data.registry import DatasetRegistry
from loop_research.errors import ResearchError
from loop_research.factors.dsl import ARITIES, FIELDS, compile_expression
from loop_research.schemas import DebugRequest, RunConfig
from loop_research.storage import Store


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    store = Store(settings.database_path)
    datasets = DatasetRegistry(settings.data_dir)

    @asynccontextmanager
    async def lifespan(app):
        process = None
        if settings.worker_autostart:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "loop_research.worker",
                    "--database",
                    str(store.path),
                ]
            )
        try:
            yield
        finally:
            if process and process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    await asyncio.to_thread(process.wait)

    app = FastAPI(title="Loop Research API", version=__version__, lifespan=lifespan)
    app.state.store = store
    app.state.settings = settings

    @app.middleware("http")
    async def context(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        public_health = request.method == "GET" and request.url.path == "/api/v1/health"
        if settings.auth_enabled and not public_health:
            if not authenticated(request.headers.get("authorization", ""), settings):
                return JSONResponse(
                    {
                        "code": "authentication_required",
                        "message": "请使用部署时设置的账号和密码登录。",
                        "details": {},
                        "request_id": request.state.request_id,
                    },
                    status_code=401,
                    headers={
                        "WWW-Authenticate": 'Basic realm="Loop Research", charset="UTF-8"',
                        "Cache-Control": "no-store",
                        "X-Request-ID": request.state.request_id,
                    },
                )
        origin = request.headers.get("origin")
        if origin and request.method not in {"GET", "HEAD", "OPTIONS"}:
            allowed = {request.url.netloc}
            if not settings.auth_enabled:
                allowed.update({"127.0.0.1:5173", "localhost:5173", "127.0.0.1:5174"})
            if urlparse(origin).netloc not in allowed:
                return JSONResponse(
                    {
                        "code": "origin_denied",
                        "message": "不允许该来源的控制请求。",
                        "details": {},
                        "request_id": request.state.request_id,
                    },
                    status_code=403,
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if settings.auth_enabled and not public_health:
            response.headers["Cache-Control"] = "no-store"
        return response

    def error_response(request: Request, code: str, message: str, status: int, details=None):
        return JSONResponse(
            {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": getattr(request.state, "request_id", None),
            },
            status_code=status,
        )

    @app.exception_handler(ResearchError)
    async def domain_error(request, exc):
        return error_response(request, exc.code, exc.message, exc.status, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo arbitrary input values (including accidentally pasted credentials).
        details = {
            "fields": [
                {"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()
            ]
        }
        return error_response(request, "validation_error", "请求参数未通过校验。", 422, details)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(request, "http_error", str(exc.detail), exc.status_code)

    @app.get("/api/v1/health")
    def health():
        worker = store.worker_status()
        ready = not settings.worker_autostart or worker == "online"
        return JSONResponse(
            {
                "status": "ok" if ready else "unavailable",
                "version": __version__,
                "database": "online",
                "worker": worker,
            },
            status_code=200 if ready else 503,
        )

    @app.get("/api/v1/capabilities")
    def capabilities():
        return {
            "phase": "scaffold",
            "available_modes": ["fixture"],
            "live_enabled": False,
            "model": settings.model_status(),
            "worker": store.worker_status(),
            "strategies": STRATEGIES,
            "mechanisms": MECHANISMS,
            "fields": list(FIELDS),
            "operators": ARITIES,
            "seed_factors": SEED_FACTORS,
            "gates": evaluate_gates({}),
            "data_count": len(datasets.list()),
            "notice": "演示模式检查代码框架，不运行市场实验或付费模型。",
        }

    @app.post("/api/v1/models/check")
    def model_check():
        return {
            **settings.model_status(),
            "remote_check_performed": False,
            "message": "仅检查服务端配置，未发送远程模型请求。",
        }

    @app.get("/api/v1/datasets")
    def list_datasets():
        return {"items": datasets.list()}

    @app.post("/api/v1/datasets/{dataset_id}/validate")
    def validate_dataset(dataset_id: str):
        return datasets.validate(dataset_id)

    @app.post("/api/v1/factors/debug")
    def debug(body: DebugRequest):
        node = compile_expression(body.expression)
        return {
            "valid": True,
            "canonical": node.canonical(),
            "fingerprint": node.fingerprint,
            "nodes": node.size,
            "depth": node.depth,
            "lookback": node.lookback,
            "tree": node.as_dict(),
            "metrics": None,
            "notice": "公式结构与量纲检查通过；未加载数据或运行回测。",
        }

    @app.get("/api/v1/runs")
    def list_runs(limit: int = Query(50, ge=1, le=100)):
        return {"items": store.list_runs(limit)}

    @app.post("/api/v1/runs", status_code=201)
    def create_run(body: RunConfig, idempotency_key: str | None = Header(None, max_length=128)):
        return store.create(body, idempotency_key)

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str):
        return store.get(run_id)

    @app.post("/api/v1/runs/{run_id}/{action}")
    def control_run(run_id: str, action: str):
        return store.control(run_id, action)

    @app.get("/api/v1/runs/{run_id}/factors")
    def list_factors(run_id: str, status: str | None = None, strategy: str | None = None):
        items = store.candidates(run_id)
        return {
            "items": [
                c
                for c in items
                if (not status or c["status"] == status)
                and (not strategy or c["strategy"] == strategy)
            ]
        }

    @app.get("/api/v1/factors/{candidate_id}")
    def get_factor(candidate_id: str):
        return store.candidate(candidate_id)

    @app.get("/api/v1/runs/{run_id}/report")
    def report(run_id: str):
        return {
            "kind": "fixture_record",
            "is_experiment": False,
            "run": store.get(run_id),
            "candidates": store.candidates(run_id),
            "notice": "仅为框架演示记录，不包含任何真实市场回测或模型效果。",
        }

    @app.get("/api/v1/runs/{run_id}/events")
    async def events(
        request: Request,
        run_id: str,
        after: int = Query(0, ge=0),
        last_event_id: str | None = Header(None),
    ):
        store.get(run_id)
        try:
            cursor = max(after, int(last_event_id or 0))
        except ValueError:
            raise ResearchError("invalid_event_id", "事件游标必须为整数。", 422) from None

        async def stream():
            nonlocal cursor
            idle = 0
            while not await request.is_disconnected():
                batch = store.events(run_id, cursor)
                for event in batch:
                    cursor = event["id"]
                    yield f"id: {cursor}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                idle += 1
                if idle % 20 == 0:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(0.3)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/v1/experiments")
    def experiments():
        return {"items": [], "status": "not_run", "message": "当前阶段搭建框架，尚未运行真实实验。"}

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise ResearchError("route_not_found", "不存在该 API。", 404)
        dist = settings.web_dist.resolve()
        resource = (dist / path).resolve()
        if not resource.is_relative_to(dist):
            raise ResearchError("route_not_found", "找不到该资源。", 404)
        if resource.is_file():
            return FileResponse(resource)
        if path.startswith("assets/"):
            raise ResearchError("asset_not_found", "找不到该静态资源。", 404)
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        return JSONResponse(
            {
                "name": "Loop Research",
                "message": "API 已启动。开发前端请运行 npm run dev:web；生产前端请先 npm run build。",
                "docs": "/docs",
            }
        )

    return app
