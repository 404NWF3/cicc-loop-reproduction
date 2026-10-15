"""Measure the production image under Railway's memory limit; no model credentials passed."""

import argparse
import asyncio
import json
import os
import secrets
import subprocess
import time
from pathlib import Path

import httpx

from loop_research.experiments.data import write_json

CONTAINER = "loop-research-resource-check"


def docker(*args):
    environment = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_TLS",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
        }
    }
    response = subprocess.run(
        ["docker", "--host=unix:///var/run/docker.sock", *args],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return response.stdout.strip()


async def profile(image: str, mode: str = "fixture"):
    target = 120 if mode == "live" else 1000
    password = secrets.token_hex(24)
    image_info = json.loads(docker("image", "inspect", image))[0]
    identifier = docker(
        "run",
        "-d",
        "--name",
        CONTAINER,
        "--memory=1g",
        "--memory-swap=1g",
        "--cpus=1",
        "--pids-limit=96",
        "-p",
        "127.0.0.1:8090:8000",
        "-e",
        "LOOP_FIXTURE_STEP_SECONDS=0.01",
        "-e",
        "LOOP_AUTH_USERNAME=resource-test",
        "-e",
        f"LOOP_AUTH_PASSWORD={password}",
        image,
    )
    samples, response_seconds, errors = [], [], []
    finished = asyncio.Event()
    transport = httpx.AsyncHTTPTransport(uds="/var/run/docker.sock")

    async def sample():
        async with httpx.AsyncClient(
            transport=transport, base_url="http://docker", timeout=8
        ) as client:
            while not finished.is_set():
                response = await client.get(f"/containers/{identifier}/stats?stream=false")
                if response.is_success:
                    stat = response.json()
                    samples.append(stat["memory_stats"].get("usage", 0))
                try:
                    await asyncio.wait_for(finished.wait(), timeout=0.25)
                except TimeoutError:
                    pass

    async def readers(client, run_id):
        for _ in range(6):
            started = time.monotonic()
            response = await client.get(f"/api/v1/runs/{run_id}")
            response_seconds.append(time.monotonic() - started)
            if response.status_code != 200:
                errors.append(response.status_code)

    try:
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8090", trust_env=False, timeout=20,
            auth=("resource-test", password),
        ) as client:
            for _ in range(120):
                try:
                    if (await client.get("/api/v1/health")).is_success:
                        break
                except httpx.TransportError:
                    pass
                await asyncio.sleep(0.25)
            else:
                raise RuntimeError("Container did not become healthy")
            await asyncio.sleep(0.5)
            capabilities = (await client.get("/api/v1/capabilities")).json()
            assert capabilities["model"]["key_present"] is False
            assert capabilities["live_enabled"] is True
            if mode == "live":
                live = (await client.get("/api/v1/live/status")).json()
                assert live["model_ready"] is False
                assert live["snapshot"]["holdout_included"] is False
            task = asyncio.create_task(sample())
            response = await client.post(
                "/api/v1/runs",
                json={
                    "name": f"Resource check: {target} {mode} attempts",
                    "mode": mode,
                    "rounds": 20 if mode == "live" else 50,
                    "batch_size": 6 if mode == "live" else 20,
                    "max_candidates": target,
                    "max_seconds": 600 if mode == "live" else 1800,
                },
            )
            response.raise_for_status()
            run_id = response.json()["id"]
            (await client.post(f"/api/v1/runs/{run_id}/start")).raise_for_status()
            started = time.monotonic()
            while time.monotonic() - started < 300:
                await asyncio.gather(*(readers(client, run_id) for _ in range(4)))
                state = (await client.get(f"/api/v1/runs/{run_id}")).json()
                if state["state"] in {"completed", "budget_exhausted", "failed"}:
                    break
                await asyncio.sleep(0.1)
            if state["state"] != "completed" or state["cursor"] != target:
                print(
                    json.dumps(
                        {
                            "state": state["state"],
                            "cursor": state["cursor"],
                            "error": state["error"],
                            "counts": state["counts"],
                            "elapsed_seconds": time.monotonic() - started,
                        },
                        indent=2,
                    ),
                    flush=True,
                )
                print(docker("logs", "--tail", "30", identifier), flush=True)
            assert state["state"] == "completed" and state["cursor"] == target
            assert state["counts"]["model_calls"] == 0
            if mode == "live":
                assert state["counts"]["accepted"] >= 6
                assert state["counts"]["backtested"] >= 6
            full = (await client.get(f"/api/v1/runs/{run_id}/report")).content
            assert len(full) < 20_000_000
            (await client.get("/api/v1/experiments")).raise_for_status()
            (await client.get("/experiments")).raise_for_status()
            (await client.get("/presentation")).raise_for_status()
            finished.set()
            await task
            health = (await client.get("/api/v1/health")).json()
        inspection = json.loads(docker("inspect", "--size", identifier))[0]
        details = json.loads(
            docker(
                "exec",
                identifier,
                "python",
                "-c",
                "import json,pathlib,importlib.util,sys; p=pathlib.Path('/sys/fs/cgroup'); "
                "print(json.dumps({'cgroup':{n:(p/n).read_text().strip() for n in "
                "['memory.max','memory.peak','memory.events'] if (p/n).exists()},"
                "'scipy_installed':importlib.util.find_spec('scipy') is not None,"
                "'venv_bytes':sum(f.stat().st_size for f in pathlib.Path(sys.prefix).rglob('*') if f.is_file()),"
                "'app_bytes':sum(f.stat().st_size for f in pathlib.Path('/app').rglob('*') if f.is_file())}))",
            )
        )
        result = {
            "status": "passed",
            "image": image,
            "image_id": image_info["Id"],
            "image_uncompressed_bytes": image_info["Size"],
            "memory_limit_bytes": inspection["HostConfig"]["Memory"],
            "cpu_limit": inspection["HostConfig"]["NanoCpus"] / 1_000_000_000,
            "sampled_memory_peak_bytes": max(samples),
            "memory_sample_count": len(samples),
            "container_writable_layer_bytes": inspection["SizeRw"],
            "mode": mode,
            "attempts": target,
            "counts": state["counts"],
            "concurrent_readers": 4,
            "http_requests": len(response_seconds),
            "http_errors": errors,
            "p95_response_seconds": sorted(response_seconds)[int(len(response_seconds) * 0.95)],
            "database_bytes": health["state_bytes"],
            "database_limit_mb": health["state_limit_mb"],
            "api_and_worker_seconds": time.monotonic() - started,
            **details,
            "storage_limit_enforced": False,
            "storage_note": "Image/layer/application bytes measured; Railway 500 MB filesystem quota not emulated.",
            "scope": f"One API + one {mode} worker, prebuilt frontend, packaged development snapshot, no API key, no model calls",
        }
        assert not errors and image_info["Size"] < 500_000_000
        assert not details["scipy_installed"]
        assert details["cgroup"].get("memory.max") == "1073741824"
        assert "oom_kill 0" in details["cgroup"].get("memory.events", "")
        write_json(Path(f"docs/resource-profile{'-live' if mode == 'live' else ''}.json"), result)
        print(json.dumps(result, indent=2))
    finally:
        finished.set()
        docker("rm", "-f", identifier)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="loop-research:railway")
    parser.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    args = parser.parse_args()
    asyncio.run(profile(args.image, args.mode))
