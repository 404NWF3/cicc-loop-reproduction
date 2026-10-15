import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from loop_research.errors import ResearchError
from loop_research.schemas import ACTIVE_STATES, TERMINAL_STATES, RunConfig


def now() -> str:
    return datetime.now(UTC).isoformat()


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class Store:
    def __init__(self, path: Path, max_state_bytes: int = 64 * 1024 * 1024, *, live_enabled=False):
        self.path = path.resolve()
        self.max_state_bytes = max_state_bytes
        self.live_enabled = live_enabled
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, config TEXT NOT NULL, config_hash TEXT NOT NULL,
                    state TEXT NOT NULL, cursor INTEGER NOT NULL DEFAULT 0,
                    checkpoint TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    started_at TEXT, error TEXT, idempotency_key TEXT UNIQUE
                );
                CREATE UNIQUE INDEX IF NOT EXISTS single_active_run ON runs((1))
                    WHERE state IN ('queued','running','pause_requested','stop_requested');
                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    ordinal INTEGER NOT NULL, fingerprint TEXT, payload TEXT NOT NULL,
                    UNIQUE(run_id, ordinal)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    type TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS event_run ON events(run_id,id);
                CREATE TABLE IF NOT EXISTS worker_lease (
                    id INTEGER PRIMARY KEY CHECK(id=1), token TEXT NOT NULL,
                    expires REAL NOT NULL
                );
            """)

    @contextmanager
    def connection(self, write: bool = False):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_size_limit=8388608")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def storage_bytes(self) -> int:
        return sum(
            p.stat().st_size
            for p in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm"))
            if p.exists()
        )

    def has_capacity(self) -> bool:
        return self.storage_bytes() < self.max_state_bytes

    def _event(self, db, run_id: str, kind: str, payload: dict):
        db.execute(
            "INSERT INTO events(run_id,type,payload,created_at) VALUES(?,?,?,?)",
            (run_id, kind, encode(payload), now()),
        )

    def _state(self, db, run_id: str, state: str, message: str = ""):
        db.execute("UPDATE runs SET state=?,updated_at=? WHERE id=?", (state, now(), run_id))
        self._event(db, run_id, "run.state", {"state": state, "message": message})

    @staticmethod
    def _require(db, run_id: str):
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise ResearchError("run_not_found", "找不到该任务。", 404)
        return row

    def create(self, config: RunConfig, key: str | None = None) -> dict:
        serialized = encode(config.model_dump())
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        with self.connection(write=True) as db:
            existing = (
                db.execute("SELECT * FROM runs WHERE idempotency_key=?", (key,)).fetchone()
                if key
                else None
            )
            if existing:
                if existing["config_hash"] != digest:
                    raise ResearchError("idempotency_conflict", "该幂等键已经用于不同配置。", 409)
                run_id = existing["id"]
            else:
                if not self.has_capacity():
                    raise ResearchError(
                        "storage_budget_exhausted", "演示存储预算已用尽；请导出并清理旧任务。", 409
                    )
                run_id = uuid.uuid4().hex[:16]
                db.execute(
                    "INSERT INTO runs(id,config,config_hash,state,created_at,updated_at,idempotency_key) VALUES(?,?,?,'draft',?,?,?)",
                    (run_id, serialized, digest, now(), now(), key),
                )
                self._event(
                    db,
                    run_id,
                    "run.created",
                    {"message": "任务已创建，配置已冻结。", "mode": config.mode},
                )
        return self.get(run_id)

    def get(self, run_id: str) -> dict:
        with self.connection() as db:
            row = self._require(db, run_id)
            counts = db.execute(
                "SELECT payload FROM candidates WHERE run_id=?", (run_id,)
            ).fetchall()
        config = json.loads(row["config"])
        candidates = [json.loads(r[0]) for r in counts]
        live = config["mode"] == "live"
        checkpoint = json.loads(row["checkpoint"])
        return {
            "id": row["id"],
            "config": config,
            "config_hash": row["config_hash"],
            "state": row["state"],
            "cursor": row["cursor"],
            "round": min(
                config["rounds"], (row["cursor"] + config["batch_size"] - 1) // config["batch_size"]
            ),
            "target": min(config["rounds"] * config["batch_size"], config["max_candidates"])
            if live
            else config["rounds"] * config["batch_size"],
            "counts": {
                "generated": len(candidates),
                "validated": sum(bool(c.get("validation")) for c in candidates)
                if live
                else sum(c["status"] == "awaiting_data" for c in candidates),
                "rejected": sum(not c.get("accepted", False) for c in candidates)
                if live
                else sum(c["status"] != "awaiting_data" for c in candidates),
                "backtested": sum(c.get("metrics") is not None for c in candidates),
                "accepted": sum(c.get("accepted", False) for c in candidates),
                "model_calls": checkpoint.get("model_requests", 0),
                "tokens": checkpoint.get("model_tokens", 0),
            },
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "started_at": row["started_at"],
            "error": row["error"],
            "checkpoint": checkpoint,
            "is_experiment": live,
            "notice": "历史快照上的现场挖掘：开发期筛选，非实时行情或独立样本外验证。"
            if live
            else "这是本地流程演示，未调用大模型、加载市场数据或生成回测收益。",
        }

    def list_runs(self, limit: int = 50) -> list[dict]:
        with self.connection() as db:
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
                )
            ]
        return [self.get(run_id) for run_id in ids]

    def control(self, run_id: str, action: str) -> dict:
        with self.connection(write=True) as db:
            row = self._require(db, run_id)
            state = row["state"]
            config = json.loads(row["config"])
            if action in {"start", "resume"}:
                if config["mode"] != "fixture" and not self.live_enabled:
                    raise ResearchError(
                        "live_pipeline_pending",
                        "当前服务未启用现场挖掘。请使用演示模式。",
                        409,
                    )
                if state in ACTIVE_STATES:
                    pass
                elif (action == "start" and state == "draft") or (
                    action == "resume" and state in {"paused", "interrupted"}
                ):
                    active = db.execute(
                        "SELECT id FROM runs WHERE state IN ('queued','running','pause_requested','stop_requested')"
                    ).fetchone()
                    if active:
                        raise ResearchError(
                            "worker_busy",
                            "已有任务正在执行，请先暂停或停止。",
                            409,
                            {"run_id": active[0]},
                        )
                    self._state(db, run_id, "queued", "任务等待 worker 处理。")
                else:
                    raise ResearchError("invalid_transition", "当前任务状态不允许该操作。", 409)
            elif action == "pause":
                if state == "running":
                    self._state(db, run_id, "pause_requested", "正在等待安全检查点。")
                elif state == "queued":
                    self._state(db, run_id, "paused", "任务尚未开始，已暂停。")
                elif state not in {"paused", "pause_requested"}:
                    raise ResearchError("invalid_transition", "该任务当前无法暂停。", 409)
            elif action == "stop":
                if state in {"running", "pause_requested"}:
                    self._state(db, run_id, "stop_requested", "正在保存最后一个检查点。")
                elif state not in TERMINAL_STATES | {"stop_requested"}:
                    self._state(db, run_id, "stopped", "任务已停止。")
            else:
                raise ResearchError("invalid_action", "不支持的任务操作。", 404)
        return self.get(run_id)

    def acquire_worker(self, token: str) -> bool:
        with self.connection(write=True) as db:
            lease = db.execute("SELECT * FROM worker_lease WHERE id=1").fetchone()
            if lease and lease["token"] != token and lease["expires"] > time.time():
                return False
            if not lease or lease["token"] != token:
                rows = db.execute(
                    "SELECT id,state FROM runs WHERE state IN ('running','pause_requested','stop_requested')"
                ).fetchall()
                for row in rows:
                    recovery = {
                        "running": "interrupted",
                        "pause_requested": "paused",
                        "stop_requested": "stopped",
                    }[row["state"]]
                    self._state(db, row["id"], recovery, "前一 worker 已退出，已保留检查点。")
            db.execute(
                "INSERT INTO worker_lease VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET token=excluded.token,expires=excluded.expires",
                (token, time.time() + 10),
            )
        return True

    @staticmethod
    def _has_lease(db, token: str) -> bool:
        return (
            db.execute(
                "SELECT 1 FROM worker_lease WHERE id=1 AND token=? AND expires>?",
                (token, time.time()),
            ).fetchone()
            is not None
        )

    def worker_status(self) -> str:
        with self.connection() as db:
            active = db.execute(
                "SELECT 1 FROM worker_lease WHERE expires>?", (time.time(),)
            ).fetchone()
        return "online" if active else "offline"

    def renew_worker(self, token: str):
        with self.connection(write=True) as db:
            db.execute(
                "UPDATE worker_lease SET expires=? WHERE id=1 AND token=? AND expires>?",
                (time.time() + 10, token, time.time()),
            )

    def checkpoint(self, run: dict, checkpoint: dict, token: str, message: str) -> bool:
        with self.connection(write=True) as db:
            if not self._has_lease(db, token):
                return False
            row = self._require(db, run["id"])
            if row["cursor"] != run["cursor"] or row["state"] not in {
                "running",
                "pause_requested",
                "stop_requested",
            }:
                return False
            if not self.has_capacity():
                self._state(db, run["id"], "budget_exhausted", "存储预算已用尽。")
                return False
            db.execute(
                "UPDATE runs SET checkpoint=?,updated_at=? WHERE id=?",
                (encode(checkpoint), now(), run["id"]),
            )
            self._event(
                db, run["id"], "run.stage", {"message": message, "stage": checkpoint.get("stage")}
            )
        return True

    def release_worker(self, token: str):
        with self.connection(write=True) as db:
            if not self._has_lease(db, token):
                return
            rows = db.execute(
                "SELECT id,state FROM runs WHERE state IN ('running','pause_requested','stop_requested')"
            ).fetchall()
            for row in rows:
                recovery = {
                    "running": "interrupted",
                    "pause_requested": "paused",
                    "stop_requested": "stopped",
                }[row["state"]]
                self._state(db, row["id"], recovery, "worker 已停止，检查点已保存。")
            db.execute("DELETE FROM worker_lease WHERE token=?", (token,))

    def next_work(self, token: str) -> dict | None:
        run_id = None
        with self.connection(write=True) as db:
            if not self._has_lease(db, token):
                return None
            row = db.execute(
                "SELECT * FROM runs WHERE state IN ('queued','running','pause_requested','stop_requested') ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            run_id = row["id"]
            if row["state"] in {"pause_requested", "stop_requested"}:
                self._state(
                    db,
                    run_id,
                    "paused" if row["state"] == "pause_requested" else "stopped",
                    "已到达安全检查点。",
                )
                return None
            if row["state"] == "queued":
                live = json.loads(row["config"])["mode"] == "live"
                self._state(
                    db,
                    run_id,
                    "running",
                    "现场挖掘已开始：历史快照、逐候选真实回测。"
                    if live
                    else "本地演示已开始，不执行市场实验。",
                )
                db.execute(
                    "UPDATE runs SET started_at=COALESCE(started_at,?) WHERE id=?", (now(), run_id)
                )
        return self.get(run_id)

    def finish(self, run_id: str, state: str, token: str, message: str):
        with self.connection(write=True) as db:
            if not self._has_lease(db, token):
                return
            row = self._require(db, run_id)
            if row["state"] not in ACTIVE_STATES:
                return
            if row["state"] == "stop_requested":
                state = "stopped"
            elif row["state"] == "pause_requested":
                state = "paused"
            if state == "failed":
                db.execute("UPDATE runs SET error=? WHERE id=?", (message, run_id))
            self._state(db, run_id, state, message)

    def record_candidate(self, run: dict, candidate: dict, checkpoint: dict, token: str) -> bool:
        with self.connection(write=True) as db:
            if not self._has_lease(db, token):
                return False
            row = self._require(db, run["id"])
            if row["cursor"] != run["cursor"] or row["state"] not in {
                "running",
                "pause_requested",
                "stop_requested",
            }:
                return False
            if not self.has_capacity():
                self._state(db, run["id"], "budget_exhausted", "演示存储预算已用尽，检查点已保留。")
                return False
            db.execute(
                "INSERT INTO candidates VALUES(?,?,?,?,?)",
                (
                    candidate["id"],
                    run["id"],
                    run["cursor"],
                    candidate.get("fingerprint"),
                    encode(candidate),
                ),
            )
            db.execute(
                "UPDATE runs SET cursor=cursor+1,checkpoint=?,updated_at=? WHERE id=?",
                (encode(checkpoint), now(), run["id"]),
            )
            self._event(
                db,
                run["id"],
                "candidate.recorded",
                {
                    "candidate_id": candidate["id"],
                    "ordinal": run["cursor"] + 1,
                    "status": candidate["status"],
                    "message": candidate["reason"],
                },
            )
        return True

    def candidates(self, run_id: str) -> list[dict]:
        with self.connection() as db:
            self._require(db, run_id)
            rows = db.execute(
                "SELECT payload FROM candidates WHERE run_id=? ORDER BY ordinal", (run_id,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def candidate(self, candidate_id: str) -> dict:
        with self.connection() as db:
            row = db.execute(
                "SELECT payload FROM candidates WHERE id=?", (candidate_id,)
            ).fetchone()
        if row is None:
            raise ResearchError("factor_not_found", "找不到该候选因子。", 404)
        return json.loads(row[0])

    def events(self, run_id: str, after: int = 0, limit: int = 200) -> list[dict]:
        with self.connection() as db:
            self._require(db, run_id)
            rows = db.execute(
                "SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id LIMIT ?",
                (run_id, after, limit),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "type": r["type"],
                "created_at": r["created_at"],
                "payload": json.loads(r["payload"]),
            }
            for r in rows
        ]
