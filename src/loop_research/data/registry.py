import hashlib
import json
import re
import shutil
from pathlib import Path

import pandas as pd

from loop_research.data.validation import validate_frame
from loop_research.errors import ResearchError
from loop_research.storage import now


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DatasetRegistry:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def directory(self, dataset_id: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", dataset_id):
            raise ResearchError("invalid_dataset_id", "数据集标识不合法。", 422)
        directory = (self.root / dataset_id).resolve()
        if not directory.is_relative_to(self.root):
            raise ResearchError("invalid_dataset_path", "数据集路径不合法。", 422)
        return directory

    def list(self) -> list[dict]:
        results = []
        for manifest in sorted(self.root.glob("*/manifest.json")):
            directory = self.directory(manifest.parent.name)
            try:
                item = json.loads(manifest.read_text())
                report = directory / "validation.json"
                item["validation"] = json.loads(report.read_text()) if report.exists() else None
                results.append(item)
            except (ValueError, OSError):
                results.append({"id": manifest.parent.name, "status": "invalid_manifest"})
        return results

    def register(self, source: Path, dataset_id: str) -> dict:
        if not source.is_file() or source.suffix.lower() != ".csv":
            raise ResearchError("invalid_source", "需要提供本地 CSV 文件。", 422)
        if source.stat().st_size > 200 * 1024 * 1024:
            raise ResearchError("source_too_large", "框架阶段只接受 200 MiB 以下的 CSV。", 422)
        directory = self.directory(dataset_id)
        if directory.exists():
            raise ResearchError("dataset_exists", "该数据集标识已存在，请使用新标识。", 409)
        report = validate_frame(pd.read_csv(source))
        if not report["valid"]:
            raise ResearchError("invalid_dataset", "CSV 校验失败。", 422, report)
        directory.mkdir(parents=True)
        try:
            shutil.copyfile(source, directory / "data.csv")
            manifest = {
                "id": dataset_id,
                "name": dataset_id,
                "source": "local_csv",
                "sha256": checksum(directory / "data.csv"),
                "created_at": now(),
                "status": "registered",
                "adjustment": "unverified",
                "is_fixture": False,
            }
            (directory / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2)
            )
            (directory / "validation.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2)
            )
        except BaseException:
            shutil.rmtree(directory)
            raise
        return manifest

    def validate(self, dataset_id: str) -> dict:
        directory = self.directory(dataset_id)
        manifest = directory / "manifest.json"
        if not manifest.is_file():
            raise ResearchError("dataset_not_found", "该数据集尚未注册。", 404)
        metadata = json.loads(manifest.read_text())
        if checksum(directory / "data.csv") != metadata["sha256"]:
            raise ResearchError("dataset_changed", "数据文件与注册的校验和不一致。", 409)
        report = validate_frame(pd.read_csv(directory / "data.csv"))
        (directory / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        return report
