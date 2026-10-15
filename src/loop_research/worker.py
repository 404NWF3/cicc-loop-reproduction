import argparse
import signal
import threading
import uuid
from pathlib import Path

from loop_research.config import Settings
from loop_research.loop.runner import step
from loop_research.storage import Store


def run_worker(database: Path, interval: float = 0.3):
    store = Store(database)
    token = uuid.uuid4().hex
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    try:
        while not stop.is_set():
            if store.acquire_worker(token):
                try:
                    step(store, token)
                except Exception as exc:
                    # Preserve state; API clients receive a useful but non-sensitive error.
                    for run in store.list_runs():
                        if run["state"] == "running":
                            store.finish(
                                run["id"],
                                "failed",
                                token,
                                f"worker 发生 {type(exc).__name__}，请查看开发日志。",
                            )
                    import traceback

                    traceback.print_exc()
            stop.wait(interval)
    finally:
        store.release_worker(token)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    settings = Settings()
    run_worker(args.database or settings.database_path, settings.fixture_step_seconds)


if __name__ == "__main__":
    main()
