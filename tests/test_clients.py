import json

import httpx
import pytest
from nutshellm.clients import (
    ExternalServiceError,
    OpenAICompatibleClient,
    ParitokClient,
)
from nutshellm.config import Settings


@pytest.mark.asyncio
async def test_paritok_contract_sends_level_and_model():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200, json={"compressed": "short", "gpu_available": True}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ParitokClient(
            Settings(paritok_api_key="test"), client
        ).compress("long result", "find bug", "log_output", "L2")
    assert result.applied
    assert captured["level"] == "L2"
    assert captured["upstream_model"] == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_paritok_offline_is_safe_passthrough():
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"compressed": "ignored", "gpu_available": False}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ParitokClient(Settings(), client).compress(
            "original", "task", "other", "L1"
        )
    assert result.compressed == "original"
    assert not result.applied


@pytest.mark.asyncio
async def test_openai_compatible_usage_is_preferred():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "answer"}}],
                "usage": {"prompt_tokens": 123, "completion_tokens": 9},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        answer = await OpenAICompatibleClient(
            Settings(
                task_model_api_key="test",
                task_reasoning_effort="low",
                task_max_output_tokens=4096,
            ),
            client,
        ).complete(task="task", context="context", system_prompt="system")
    assert answer.text == "answer"
    assert answer.usage.input_tokens == 123
    assert answer.usage.output_tokens == 9
    assert not answer.usage.estimated
    assert captured["reasoning_effort"] == "low"
    assert captured["max_tokens"] == 4096


@pytest.mark.asyncio
async def test_task_model_rate_limit_is_classified_before_body_parsing():
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ExternalServiceError, match="rate limit"):
            await OpenAICompatibleClient(
                Settings(task_model_max_retries=0), client
            ).complete(
                task="task", context="context", system_prompt="system"
            )


@pytest.mark.asyncio
async def test_task_model_retries_once_after_provider_delay():
    calls = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                json=[
                    {
                        "error": {
                            "message": "Quota exceeded. Please retry in 0.01s."
                        }
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "answer"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    settings = Settings(
        task_model_max_retries=1,
        task_model_retry_max_delay_seconds=1,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        answer = await OpenAICompatibleClient(settings, client).complete(
            task="task", context="context", system_prompt="system"
        )
    assert calls == 2
    assert answer.text == "answer"
