"""Small model-facing service. Deliberately disconnected from fixture tasks."""

import json
from importlib.resources import files

from pydantic import BaseModel, ConfigDict, Field

from loop_research.catalog import MECHANISMS
from loop_research.errors import ResearchError
from loop_research.factors.dsl import ARITIES, FIELDS, compile_expression
from loop_research.models.deepseek import DeepSeekClient
from loop_research.schemas import CandidateBatch, ModelCandidate, ReviewResponse


class DevelopmentContext(BaseModel):
    """No dataset rows, arbitrary instruction blocks, or holdout metric fields."""

    model_config = ConfigDict(extra="forbid")
    requested_count: int = Field(2, ge=1, le=10)
    parent_expressions: list[str] = Field(default_factory=list, max_length=10)
    mechanism_coverage: dict[str, int] = Field(default_factory=dict)
    rejection_codes: list[str] = Field(default_factory=list, max_length=30)
    blocked_skeletons: list[str] = Field(default_factory=list, max_length=30)


def prompt(name: str) -> str:
    return files("loop_research").joinpath(f"prompts/{name}.md").read_text(encoding="utf-8")


class FactorAssistant:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    async def generate(self, context: DevelopmentContext) -> dict:
        payload = {
            **context.model_dump(),
            "allowed_fields": list(FIELDS),
            "operators_and_arities": ARITIES,
            "mechanisms": MECHANISMS,
        }
        response = await self.client.generate_json(
            [
                {"role": "system", "content": prompt("generator")},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            CandidateBatch,
        )
        batch = CandidateBatch.model_validate(response["output"])
        if len(batch.candidates) > context.requested_count:
            raise ResearchError("model_batch_too_large", "模型返回的候选数量超过请求上限。", 502)
        for candidate in batch.candidates:
            compile_expression(candidate.expression)
            if candidate.mechanism not in MECHANISMS:
                raise ResearchError("invalid_mechanism", "模型返回了未定义的机制。", 502)
        return response

    async def review(self, candidate: ModelCandidate) -> dict:
        compile_expression(candidate.expression)
        # Deliberately omit the generator's persuasive explanation and any performance numbers.
        payload = {
            "expression": candidate.expression,
            "mechanism": candidate.mechanism,
            "field_names": list(FIELDS),
            "data_frequency": "daily_OHLCV",
            "timing": "signal_after_close_trade_next_open",
        }
        return await self.client.generate_json(
            [
                {"role": "system", "content": prompt("reviewer")},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            ReviewResponse,
        )
