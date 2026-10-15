"""Exercise the built image, including auth, SSE, SIGTERM and volume reuse.

Run after `docker build -t loop-research:smoke .` using a local Docker daemon.
Only the test's uniquely named containers and volume are removed.
"""

import argparse
import base64
import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="loop-research:smoke")
    args = parser.parse_args()
    prefix = "loop-smoke-" + uuid.uuid4().hex[:12]
    volume = prefix + "-data"
    containers = []
    username = "smoke"
    password = secrets.token_hex(24)
    authorization = "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
    environment = {
        **os.environ,
        "LOOP_AUTH_USERNAME": username,
        "LOOP_AUTH_PASSWORD": password,
        "PORT": "8087",  # Deliberately different from the image's default port.
    }
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def docker(*command, check=True):
        return subprocess.run(
            ["docker", *command],
            capture_output=True,
            text=True,
            check=check,
            env=environment,
        )

    def request(base, path, body=None, *, authorized=True, origin=None):
        headers = {"Authorization": authorization} if authorized else {}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if origin:
            headers["Origin"] = origin
        try:
            with http.open(
                urllib.request.Request(base + path, data=payload, headers=headers), timeout=5
            ) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def start(suffix):
        name = prefix + suffix
        containers.append(name)
        docker(
            "run",
            "--detach",
            "--name",
            name,
            "--publish",
            "127.0.0.1::8087",
            "--mount",
            f"type=volume,source={volume},target=/data",
            "--env",
            "LOOP_AUTH_USERNAME",
            "--env",
            "LOOP_AUTH_PASSWORD",
            "--env",
            "PORT",
            args.image,
        )
        address = docker("port", name, "8087/tcp").stdout.strip().splitlines()[0]
        base = "http://" + address
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                status, data = request(base, "/api/v1/health", authorized=False)
                if status == 200 and json.loads(data)["worker"] == "online":
                    return name, base
            except (OSError, ValueError):
                pass
            time.sleep(0.3)
        raise AssertionError("Container did not become ready with an online worker")

    try:
        result = docker("run", "--rm", args.image, check=False)
        assert result.returncode != 0 and "LOOP_AUTH_USERNAME" in result.stderr, result.stderr
        print("PASS: image refuses startup without credentials", flush=True)
        docker("volume", "create", volume)
        name, base = start("-first")
        for path in ("/", "/console", "/docs", "/openapi.json", "/api/v1/runs"):
            assert request(base, path, authorized=False)[0] == 401, path
        status, body = request(base, "/console")
        assert status == 200 and b'<div id="root">' in body
        assert request(base, "/api/v1/runs", {}, origin="https://unrelated.example")[0] == 403
        status, body = request(
            base,
            "/api/v1/runs",
            {"name": "Docker smoke", "rounds": 1, "batch_size": 1},
            origin=base,
        )
        assert status == 201
        run_id = json.loads(body)["id"]
        assert request(base, f"/api/v1/runs/{run_id}/start", {}, origin=base)[0] == 200
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            status, body = request(base, f"/api/v1/runs/{run_id}")
            run = json.loads(body)
            if run["state"] == "completed":
                break
            time.sleep(0.3)
        else:
            raise AssertionError("Worker did not complete the fixture task")
        assert run["cursor"] == 1 and run["counts"]["model_calls"] == 0
        events = f"/api/v1/runs/{run_id}/events"
        assert request(base, events, authorized=False)[0] == 401
        with http.open(
            urllib.request.Request(base + events, headers={"Authorization": authorization}),
            timeout=5,
        ) as response:
            assert response.headers["Content-Type"].startswith("text/event-stream")
            assert response.readline().startswith(b"id:")
            assert response.readline().startswith(b"data:")
        print("PASS: frontend, authentication, worker task and SSE on dynamic PORT", flush=True)
        docker("stop", "--time", "20", name)
        assert docker("inspect", "--format", "{{.State.ExitCode}}", name).stdout.strip() == "0"
        _, base = start("-second")
        status, body = request(base, f"/api/v1/runs/{run_id}")
        restored = json.loads(body)
        assert status == 200 and restored["state"] == "completed" and restored["cursor"] == 1
        status, body = request(base, f"/api/v1/runs/{run_id}/factors")
        assert status == 200 and len(json.loads(body)["items"]) == 1
        print("PASS: graceful stop and SQLite persistence after container replacement", flush=True)
    finally:
        for name in containers:
            docker("rm", "--force", name, check=False)
        docker("volume", "rm", volume, check=False)


if __name__ == "__main__":
    main()
