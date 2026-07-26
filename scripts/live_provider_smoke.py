"""Minimal live-provider connectivity check."""

from __future__ import annotations

import asyncio

import httpx
from nutshellm.clients import OpenAICompatibleClient, ParitokClient
from nutshellm.config import Settings


async def main() -> None:
    settings = Settings.from_env()
    async with httpx.AsyncClient() as client:
        answer = await OpenAICompatibleClient(settings, client).complete(
            task="Return only the word OK.",
            context="This is a connectivity check.",
            system_prompt="Follow the task exactly.",
        )
        print(
            "TASK_MODEL_SMOKE: ok "
            f"input_tokens={answer.usage.input_tokens} "
            f"output_tokens={answer.usage.output_tokens}"
        )
        compressed = await ParitokClient(settings, client).compress(
            "status ok\nstatus ok\nstatus ok\nerror worker-7 timeout",
            "identify the anomalous worker",
            "log_output",
            "L1",
        )
        print(
            "PARITOK_SMOKE: ok "
            f"applied={compressed.applied} "
            f"output_chars={len(compressed.compressed)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
