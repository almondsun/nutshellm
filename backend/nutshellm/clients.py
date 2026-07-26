"""External service adapters with narrow, testable contracts."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings
from .schemas import ModelAnswer, ModelUsage
from .tokenizer import count_tokens


class ExternalServiceError(RuntimeError):
    """A sanitized external-service failure safe to expose to callers."""

MAX_UPSTREAM_RESPONSE_BYTES = 2_000_000


async def _bounded_body(response: httpx.Response) -> bytes:
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > MAX_UPSTREAM_RESPONSE_BYTES:
            raise ExternalServiceError("Upstream response exceeded the size limit")
    return bytes(body)


async def _bounded_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = json.loads(await _bounded_body(response))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ExternalServiceError("Upstream returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ExternalServiceError("Upstream returned invalid JSON")
    return data


async def _retry_delay(response: httpx.Response, maximum: float) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return min(maximum, max(0.0, float(retry_after)))
        except ValueError:
            pass
    try:
        data = json.loads(await _bounded_body(response))
    except (ValueError, UnicodeDecodeError):
        return min(maximum, 1.0)
    if isinstance(data, list) and data:
        data = data[0]
    message = ""
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        message = str(data["error"].get("message", ""))
    match = re.search(r"retry in ([0-9.]+)s", message, re.IGNORECASE)
    return min(maximum, float(match.group(1)) if match else 1.0)


@dataclass(frozen=True)
class CompressionResponse:
    compressed: str
    applied: bool


class ParitokClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self.settings = settings
        self.http = http_client

    async def compress(
        self, content: str, task: str, kind: str, level: str
    ) -> CompressionResponse:
        payload = {
            "model": self.settings.paritok_model,
            "content": content,
            "query": task,
            "kind": kind,
            "level": level,
            "upstream_model": self.settings.task_model,
        }
        try:
            async with self.http.stream(
                "POST",
                f"{self.settings.paritok_base_url}/compress",
                headers={"Authorization": f"Bearer {self.settings.paritok_api_key}"},
                json=payload,
                timeout=self.settings.paritok_timeout_seconds,
            ) as response:
                if response.status_code in {401, 403}:
                    raise ExternalServiceError("Paritok authorization was rejected")
                if response.status_code == 429:
                    raise ExternalServiceError("Paritok rate limit was reached")
                if response.status_code >= 400:
                    raise ExternalServiceError(
                        f"Paritok returned HTTP {response.status_code}"
                    )
                data = await _bounded_json(response)
        except httpx.TimeoutException as exc:
            raise ExternalServiceError("Paritok compression timed out") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Paritok compression is unavailable") from exc
        compressed = data.get("compressed")
        available = data.get("gpu_available") is True
        if not available or not isinstance(compressed, str) or not compressed.strip():
            return CompressionResponse(content, False)
        compressed = compressed.strip()
        if len(compressed) > min(len(content), self.settings.max_context_chars):
            return CompressionResponse(content, False)
        return CompressionResponse(compressed, compressed != content.strip())


class OpenAICompatibleClient:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self.settings = settings
        self.http = http_client

    async def complete(
        self,
        *,
        task: str,
        context: str,
        system_prompt: str,
        model: str | None = None,
    ) -> ModelAnswer:
        selected_model = model or self.settings.task_model
        payload = {
            "model": selected_model,
            "temperature": 0,
            "max_tokens": self.settings.task_max_output_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TASK:\n{task}\n\nCONTEXT:\n{context}"},
            ],
        }
        if self.settings.task_reasoning_effort:
            payload["reasoning_effort"] = self.settings.task_reasoning_effort
        started = time.perf_counter()
        try:
            for attempt in range(self.settings.task_model_max_retries + 1):
                async with self.http.stream(
                    "POST",
                    f"{self.settings.task_model_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.task_model_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=120,
                ) as response:
                    if response.status_code in {401, 403}:
                        raise ExternalServiceError(
                            "Task model authorization was rejected"
                        )
                    if response.status_code == 429:
                        if attempt < self.settings.task_model_max_retries:
                            delay = await _retry_delay(
                                response,
                                self.settings.task_model_retry_max_delay_seconds,
                            )
                            await asyncio.sleep(delay)
                            continue
                        raise ExternalServiceError(
                            "Task model rate limit was reached"
                        )
                    if response.status_code >= 400:
                        raise ExternalServiceError(
                            f"Task model returned HTTP {response.status_code}"
                        )
                    data = await _bounded_json(response)
                    break
        except httpx.TimeoutException as exc:
            raise ExternalServiceError("Task model timed out") from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError("Task model is unavailable") from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ExternalServiceError("Task model returned an invalid response") from exc
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            raise ExternalServiceError("Task model returned no text")
        if len(content) > self.settings.task_max_output_tokens * 16:
            raise ExternalServiceError("Task model output exceeded the size limit")
        usage = data.get("usage") or {}
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        estimated = not isinstance(input_tokens, int) or not isinstance(output_tokens, int)
        if not isinstance(input_tokens, int):
            input_tokens = count_tokens(system_prompt + task + context, selected_model)
        if not isinstance(output_tokens, int):
            output_tokens = count_tokens(content, selected_model)
        return ModelAnswer(
            text=content,
            usage=ModelUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round((time.perf_counter() - started) * 1000),
                estimated=estimated,
            ),
        )

    async def judge(
        self, task: str, baseline: str, optimized: str
    ) -> tuple[dict[str, Any], ModelUsage]:
        prompt = (
            "Compare two answers for the same task. Ignore writing style. Return JSON "
            "only with keys equivalent (boolean), score (0 to 1), and reason. The "
            "optimized answer passes only if every material fact is preserved and it "
            "is at least as useful as the baseline."
        )
        answer = await self.complete(
            task=task,
            context=f"BASELINE:\n{baseline}\n\nOPTIMIZED:\n{optimized}",
            system_prompt=prompt,
            model=self.settings.judge_model or self.settings.task_model,
        )
        raw = answer.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:].lstrip()
        try:
            result = json.loads(raw)
        except ValueError:
            result = {
                "equivalent": False,
                "score": 0,
                "reason": "judge returned invalid JSON",
            }
        return result, answer.usage
