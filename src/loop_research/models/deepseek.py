"""Explicit official API adapter. Not invoked by the scaffold's fixture worker."""

import asyncio
import json
import time
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError

from loop_research.config import Settings
from loop_research.errors import ResearchError


@dataclass
class CallBudget:
    max_requests: int = 30
    max_tokens: int = 60_000
    requests: int = 0
    tokens: int = 0

    def reserve(self, tokens: int):
        if self.requests >= self.max_requests or self.tokens + tokens > self.max_tokens:
            raise ResearchError("model_budget_exhausted", "模型调用预算已用尽。", 409)
        self.requests += 1
        self.tokens += tokens

    def settle(self, reserved: int, actual: int | None):
        if isinstance(actual, int) and actual >= 0:
            self.tokens += actual - reserved


class DeepSeekClient:
    def __init__(
        self,
        settings: Settings,
        budget: CallBudget | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not settings.deepseek_api_key or not settings.deepseek_model:
            raise ResearchError(
                "model_not_configured", "请在服务端配置密钥和核实后的官方模型 ID。", 409
            )
        self.settings = settings
        self.budget = budget or CallBudget()
        self.transport = transport

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(transport=self.transport, timeout=15) as client:
            try:
                response = await client.get(
                    f"{self.settings.deepseek_base_url}/models", headers=self._headers()
                )
            except httpx.TransportError as exc:
                raise ResearchError(
                    "model_connection_failed", "无法连接 DeepSeek 官方接口。", 502
                ) from exc
            self._check_status(response)
            try:
                return [m["id"] for m in response.json()["data"]]
            except (KeyError, TypeError, ValueError) as exc:
                raise ResearchError(
                    "model_response_invalid", "模型列表响应格式不正确。", 502
                ) from exc

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _check_status(response: httpx.Response):
        if response.is_success:
            return
        code = {
            401: "model_auth_failed",
            403: "model_access_denied",
            402: "model_balance_required",
            429: "model_rate_limited",
        }.get(response.status_code, "model_http_error")
        raise ResearchError(
            code,
            f"DeepSeek 请求失败（HTTP {response.status_code}）。",
            502,
            {"upstream_status": response.status_code},
        )

    async def generate_json(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        *,
        max_tokens: int = 1200,
        deadline_seconds: float = 90,
    ) -> dict:
        if not 1 <= max_tokens <= 4096 or not 0 < deadline_seconds <= 1800:
            raise ValueError("Invalid generation limits")
        deadline = time.monotonic() + deadline_seconds
        # UTF-8 byte count is a conservative input estimate; unknown usage retains reservation.
        reserve = len(json.dumps(messages, ensure_ascii=False).encode()) + max_tokens + 256
        async with httpx.AsyncClient(transport=self.transport) as client:
            for attempt in range(3):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ResearchError("model_deadline", "模型调用时间预算已用尽。", 409)
                self.budget.reserve(reserve)
                started = time.monotonic()
                try:
                    async with asyncio.timeout(remaining):
                        response = await client.post(
                            f"{self.settings.deepseek_base_url}/chat/completions",
                            headers=self._headers(),
                            json={
                                "model": self.settings.deepseek_model,
                                "messages": messages,
                                "max_tokens": max_tokens,
                                "response_format": {"type": "json_object"},
                            },
                            timeout=httpx.Timeout(min(60, remaining), connect=min(10, remaining)),
                        )
                except (httpx.TransportError, TimeoutError) as exc:
                    # A server may have processed this request. Do not silently double bill it.
                    raise ResearchError(
                        "model_outcome_unknown", "请求结果未知；保留预算，未自动重发。", 502
                    ) from exc
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    try:
                        delay = max(
                            0, min(10, float(response.headers.get("Retry-After", 2**attempt)))
                        )
                    except ValueError:
                        delay = 2**attempt
                    if delay >= deadline - time.monotonic():
                        raise ResearchError("model_deadline", "重试将超过时间预算。", 409)
                    await asyncio.sleep(delay)
                    continue
                self._check_status(response)
                try:
                    body = response.json()
                    usage = body.get("usage", {})
                    self.budget.settle(reserve, usage.get("total_tokens"))
                    parsed = schema.model_validate_json(body["choices"][0]["message"]["content"])
                    return {
                        "output": parsed.model_dump(),
                        "usage": usage,
                        "model": body.get("model", self.settings.deepseek_model),
                        "request_id": body.get("id"),
                        "seconds": time.monotonic() - started,
                    }
                except (ValueError, KeyError, TypeError, IndexError, ValidationError) as exc:
                    raise ResearchError(
                        "model_output_invalid", "模型响应未通过结构校验。", 502
                    ) from exc
        raise ResearchError("model_request_failed", "模型调用失败。", 502)
