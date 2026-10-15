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
    experiment = commands.add_parser(
        "experiment", help="Run a bounded local E0–E3 market experiment"
    )
    experiment.add_argument("--config", type=Path, default=Path("configs/local_experiment.yaml"))
    experiment.add_argument("--id", required=True)
    experiment.add_argument("--data-dir", type=Path, default=Path("data/stocknet-330708b5"))
    experiment.add_argument(
        "--replay", type=Path, help="Replay archived responses, with zero API calls"
    )
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

            run_worker(settings.database_path, settings.fixture_step_seconds, settings.state_max_mb)
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
        elif args.command == "experiment":
            import asyncio
            import fcntl
            import re

            from loop_research.experiments.runner import run_experiment

            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", args.id):
                parser.error("Experiment ID must be a simple directory name")
            ledger = Path("artifacts/budgets/deepseek.sqlite3")
            ledger.parent.mkdir(parents=True, exist_ok=True)
            with ledger.with_suffix(".lock").open("w") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    parser.error("Another local experiment already holds the shared budget lock")
                result = asyncio.run(
                    run_experiment(
                        yaml.safe_load(args.config.read_text()),
                        args.data_dir,
                        Path("artifacts") / args.id,
                        ledger,
                        replay=args.replay,
                    )
                )
            print(
                json.dumps(
                    {k: result[k] for k in ("id", "status", "budget", "seconds")},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            if result["status"] != "completed":
                parser.exit(1, "实验只完成部分工作，详见 report.json；未解封 holdout。\n")
    except ResearchError as exc:
        parser.exit(1, f"{exc.code}: {exc.message}\n")


if __name__ == "__main__":
    main()
