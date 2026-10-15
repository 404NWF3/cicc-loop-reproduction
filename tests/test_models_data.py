import asyncio
import json

import httpx
import pandas as pd
import pytest

from loop_research.config import Settings
from loop_research.data.registry import DatasetRegistry
from loop_research.data.validation import validate_frame
from loop_research.errors import ResearchError
from loop_research.models.agent import DevelopmentContext, FactorAssistant
from loop_research.models.deepseek import CallBudget, DeepSeekClient
from loop_research.schemas import ModelCandidate, ReviewResponse


def test_deepseek_structured_output_and_budget_with_mock_transport():
    def reply(request):
        assert request.url.host == "api.deepseek.com"
        assert json.loads(request.content)["model"] == "test-model"
        return httpx.Response(
            200,
            json={
                "id": "fixture-response",
                "usage": {"total_tokens": 24},
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "verdict": "approve",
                                    "reason_code": "fixture",
                                    "explanation": "test",
                                }
                            )
                        }
                    }
                ],
            },
        )

    settings = Settings(_env_file=None, deepseek_api_key="fixture-key", deepseek_model="test-model")
    budget = CallBudget(max_requests=1, max_tokens=5000)
    client = DeepSeekClient(settings, budget, httpx.MockTransport(reply))
    output = asyncio.run(
        client.generate_json([{"role": "user", "content": "Return JSON"}], ReviewResponse)
    )
    assert output["output"]["verdict"] == "approve"
    assert budget.tokens == 24 and budget.requests == 1
    with pytest.raises(ResearchError, match="预算"):
        asyncio.run(client.generate_json([], ReviewResponse))


def test_unknown_network_outcome_is_not_retried():
    calls = []

    def reply(request):
        calls.append(request)
        raise httpx.ReadTimeout("fixture timeout")

    client = DeepSeekClient(
        Settings(_env_file=None, deepseek_api_key="fixture", deepseek_model="test"),
        transport=httpx.MockTransport(reply),
    )
    with pytest.raises(ResearchError, match="结果未知"):
        asyncio.run(client.generate_json([], ReviewResponse))
    assert len(calls) == 1 and client.budget.tokens > 0


def test_agent_roles_use_separate_structured_contexts():
    requests = []
    candidate = {
        "name": "fixture",
        "expression": "ts_mean(gap, 5)",
        "mechanism": "overnight",
        "hypothesis": "unverified persuasive claim",
        "expected_direction": 1,
    }

    def reply(request):
        body = json.loads(request.content)
        requests.append(body)
        output = (
            {"candidates": [candidate]}
            if len(requests) == 1
            else {
                "verdict": "uncertain",
                "reason_code": "needs_data",
                "explanation": "No evidence yet",
            }
        )
        return httpx.Response(
            200,
            json={
                "usage": {"total_tokens": 20},
                "choices": [{"message": {"content": json.dumps(output)}}],
            },
        )

    client = DeepSeekClient(
        Settings(_env_file=None, deepseek_api_key="fixture", deepseek_model="test"),
        transport=httpx.MockTransport(reply),
    )
    agent = FactorAssistant(client)
    generated = asyncio.run(agent.generate(DevelopmentContext(requested_count=1)))
    assert generated["output"]["candidates"][0]["expression"] == candidate["expression"]
    reviewed = asyncio.run(agent.review(ModelCandidate.model_validate(candidate)))
    assert reviewed["output"]["verdict"] == "uncertain"
    review_context = json.loads(requests[1]["messages"][1]["content"])
    assert "hypothesis" not in review_context and "holdout" not in review_context
    assert client.budget.requests == 2


def test_local_csv_contract_and_tamper_detection(tmp_path):
    frame = pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02"],
            "symbol": ["A", "A"],
            "open": [10, 11],
            "close": [11, 12],
            "high": [12, 13],
            "low": [9, 10],
            "volume": [100, 200],
        }
    )
    source = tmp_path / "fixture.csv"
    frame.to_csv(source, index=False)
    registry = DatasetRegistry(tmp_path / "datasets")
    registry.register(source, "tiny-fixture")
    assert registry.validate("tiny-fixture")["valid"]
    duplicated = pd.concat([frame, frame.iloc[:1]])
    assert not validate_frame(duplicated)["valid"]
    with pytest.raises(ResearchError):
        registry.directory("../escape")
    destination = tmp_path / "datasets/tiny-fixture/data.csv"
    destination.write_text(destination.read_text() + "\n")
    with pytest.raises(ResearchError, match="校验和"):
        registry.validate("tiny-fixture")
