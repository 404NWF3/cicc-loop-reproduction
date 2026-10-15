"""Reviewed static result bundles. No market data or model responses are deployed."""

import json
from importlib.resources import files


def bundled_results() -> list[dict]:
    directory = files("loop_research.results")
    results = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in directory.iterdir()
        if path.name.endswith(".json") and path.is_file()
    ]
    return sorted(results, key=lambda r: (r["started_at_utc"], r["id"]), reverse=True)
