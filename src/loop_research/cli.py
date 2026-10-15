import argparse
import json
from pathlib import Path

import yaml

from loop_research.config import Settings
from loop_research.data.registry import DatasetRegistry
from loop_research.errors import ResearchError
from loop_research.schemas import RunConfig
from loop_research.storage import Store


def main():
    parser = argparse.ArgumentParser(
        description="Loop Research — lightweight factor research scaffold"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start the API and its local worker")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    doctor = commands.add_parser("doctor", help="Check local configuration without a model request")
    doctor.add_argument("--offline", action="store_true")
    commands.add_parser("worker", help="Run an independent worker")
    run = commands.add_parser(
        "run", help="Create and queue a fixture task (requires a running worker)"
    )
    run.add_argument("--config", type=Path, default=Path("configs/smoke.yaml"))
    run.add_argument("--mode", choices=["fixture", "live"])
    data = commands.add_parser("data", help="Register/validate local CSV data; never downloads")
    actions = data.add_subparsers(dest="data_action", required=True)
    register = actions.add_parser("register")
    register.add_argument("--csv", type=Path, required=True)
    register.add_argument("--id", required=True)
    validate = actions.add_parser("validate")
    validate.add_argument("id")
    args = parser.parse_args()
    try:
        settings = Settings()
        if args.command == "serve":
            if args.host not in {"127.0.0.1", "localhost", "::1"} and not settings.auth_enabled:
                parser.error("公网监听必须设置 LOOP_AUTH_USERNAME 和 LOOP_AUTH_PASSWORD。")
            import uvicorn

            uvicorn.run(
                "loop_research.api:create_app",
                factory=True,
                host=args.host,
                port=args.port,
                reload=args.reload,
            )
        elif args.command == "worker":
            from loop_research.worker import run_worker

            run_worker(settings.database_path, settings.fixture_step_seconds)
        elif args.command == "doctor":
            result = {
                "database": "online",
                "model": settings.model_status(),
                "mode": "fixture",
                "network_requests": 0,
                "worker": Store(settings.database_path).worker_status(),
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "run":
            options = yaml.safe_load(args.config.read_text())
            if args.mode:
                options["mode"] = args.mode
            store = Store(settings.database_path)
            if store.worker_status() != "online":
                raise ResearchError(
                    "worker_offline", "请先运行 loop-research serve 或 loop-research worker。", 409
                )
            run = store.create(RunConfig.model_validate(options))
            result = store.control(run["id"], "start")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "data":
            registry = DatasetRegistry(settings.data_dir)
            result = (
                registry.register(args.csv, args.id)
                if args.data_action == "register"
                else registry.validate(args.id)
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except ResearchError as exc:
        parser.exit(1, f"{exc.code}: {exc.message}\n")


if __name__ == "__main__":
    main()
