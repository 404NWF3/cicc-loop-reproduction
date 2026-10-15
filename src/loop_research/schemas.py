from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RunState(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSE_REQUESTED = "pause_requested"
    PAUSED = "paused"
    STOP_REQUESTED = "stop_requested"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    BUDGET_EXHAUSTED = "budget_exhausted"


ACTIVE_STATES = {"queued", "running", "pause_requested", "stop_requested"}
TERMINAL_STATES = {"completed", "stopped", "failed", "budget_exhausted"}


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field("本地流程演示", min_length=1, max_length=80)
    mode: Literal["fixture", "live"] = "fixture"
    rounds: int = Field(3, ge=1, le=50)
    batch_size: int = Field(6, ge=1, le=20)
    seed: int = Field(42, ge=0, le=2**31 - 1)
    fsa_enabled: bool = True
    max_candidates: int = Field(100, ge=1, le=1000)
    max_seconds: int = Field(600, ge=5, le=1800)
    dataset_id: str | None = Field(None, pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    generator: Literal["local", "deepseek"] = "local"
    max_model_cny: float = Field(0.5, gt=0, le=1)

    @model_validator(mode="after")
    def bounded_live_run(self):
        if self.mode == "live" and (
            self.rounds * self.batch_size > 120
            or self.max_candidates > 120
            or self.max_seconds > 600
            or self.batch_size > 12
        ):
            raise ValueError("现场挖掘每次最多 120 个候选、600 秒、每批 12 个")
        return self

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("任务名称不能为空")
        return value.strip()


class DebugRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str = Field(min_length=1, max_length=2000)


class ModelCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    expression: str = Field(min_length=1, max_length=2000)
    mechanism: str = Field(min_length=1, max_length=64)
    hypothesis: str = Field(min_length=1, max_length=1000)
    expected_direction: Literal[-1, 1] = 1


class CandidateBatch(BaseModel):
    candidates: list[ModelCandidate] = Field(min_length=1, max_length=20)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["approve", "reject", "uncertain"]
    reason_code: str = Field(max_length=80)
    explanation: str = Field(max_length=2000)
