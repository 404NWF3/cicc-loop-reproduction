"""Crash-safe reservations, shared across all local experiment branches and restarts."""

import sqlite3
from pathlib import Path

from loop_research.errors import ResearchError


class PersistentBudget:
    # Official peak Flash prices (2026-10-15): input 2, cache-hit .04, output 8 CNY/M.
    # Charge every reserved/actual token at 8 CNY/M, so accounting is an upper bound.
    RATE_MICROCNY = 8

    def __init__(self, path: Path, *, max_cny: float = 40, max_requests=60, max_tokens=120_000):
        if not 0 < max_cny <= 40 or not 0 < max_requests <= 60 or not 0 < max_tokens <= 120_000:
            raise ValueError("Local experiment limits cannot exceed the authorized budget")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.pending = path, None
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS limits (id INTEGER PRIMARY KEY, "
                "microcny INTEGER, requests INTEGER, tokens INTEGER)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, "
                "reserved INTEGER, charged INTEGER, state TEXT, created TEXT "
                "DEFAULT CURRENT_TIMESTAMP)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS carried (id INTEGER PRIMARY KEY, requests INTEGER, tokens INTEGER)"
            )
            db.execute("INSERT OR IGNORE INTO carried VALUES(1,0,0)")
            db.execute(
                "INSERT OR IGNORE INTO limits VALUES(1,?,?,?)",
                (int(max_cny * 1_000_000), max_requests, max_tokens),
            )
            # Opening an existing ledger may tighten limits, never silently raise them.
            db.execute(
                "UPDATE limits SET microcny=min(microcny,?), "
                "requests=min(requests,?), tokens=min(tokens,?) WHERE id=1",
                (int(max_cny * 1_000_000), max_requests, max_tokens),
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def carry_floor(self, requests: int, tokens: int):
        """Carry published historical usage into a new persistent deployment, never reset it."""
        if type(requests) is not int or type(tokens) is not int or min(requests, tokens) < 0:
            raise ValueError("Nonnegative usage totals required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count, charged = db.execute(
                "SELECT count(*),coalesce(sum(charged),0) FROM calls"
            ).fetchone()
            old_calls, old_tokens = db.execute(
                "SELECT requests,tokens FROM carried WHERE id=1"
            ).fetchone()
            db.execute(
                "UPDATE carried SET requests=?,tokens=? WHERE id=1",
                (max(old_calls, requests - count), max(old_tokens, tokens - charged)),
            )

    def reserve(self, tokens: int):
        if type(tokens) is not int or tokens < 1:
            raise ValueError("Positive conservative token reservation required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            max_money, max_calls, max_tokens = db.execute(
                "SELECT microcny,requests,tokens FROM limits WHERE id=1"
            ).fetchone()
            calls, charged = db.execute(
                "SELECT count(*),coalesce(sum(charged),0) FROM calls"
            ).fetchone()
            carry_calls, carry_tokens = db.execute(
                "SELECT requests,tokens FROM carried WHERE id=1"
            ).fetchone()
            calls, charged = calls + carry_calls, charged + carry_tokens
            if (
                calls >= max_calls
                or charged + tokens > max_tokens
                or (charged + tokens) * self.RATE_MICROCNY > max_money
            ):
                raise ResearchError(
                    "model_budget_exhausted", "持久化模型预算不足，未发送请求。", 409
                )
            row = db.execute(
                "INSERT INTO calls(reserved,charged,state) VALUES(?,?,'reserved')", (tokens, tokens)
            )
            self.pending = row.lastrowid

    def settle(self, reserved: int, actual: int | None):
        # Missing, malformed or unknown usage keeps the entire reservation.
        if type(actual) is not int or actual < 0:
            return
        with self.connect() as db:
            db.execute(
                "UPDATE calls SET charged=?,state='settled' WHERE id=? AND state='reserved'",
                (actual, self.pending),
            )
        self.pending = None

    def summary(self) -> dict:
        with self.connect() as db:
            calls, tokens, unresolved = db.execute(
                "SELECT count(*),coalesce(sum(charged),0),"
                "coalesce(sum(state='reserved'),0) FROM calls"
            ).fetchone()
            cap = db.execute("SELECT microcny FROM limits WHERE id=1").fetchone()[0] / 1_000_000
            carry_calls, carry_tokens = db.execute(
                "SELECT requests,tokens FROM carried WHERE id=1"
            ).fetchone()
            calls, tokens = calls + carry_calls, tokens + carry_tokens
        return {
            "requests": calls,
            "tokens_charged_or_reserved": tokens,
            "cost_upper_bound_cny": tokens * self.RATE_MICROCNY / 1_000_000,
            "unresolved_requests": unresolved,
            "hard_cap_cny": cap,
            "pricing_source": "https://api-docs.deepseek.com/zh-cn/quick_start/pricing",
            "pricing_basis": "all tokens at peak output price 8 CNY/million; conservative",
        }
