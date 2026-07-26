"""Run one curated scenario against the configured live providers."""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

import httpx
from nutshellm.clients import OpenAICompatibleClient, ParitokClient
from nutshellm.config import Settings
from nutshellm.orchestrator import RunEngine
from nutshellm.schemas import RunCreate


async def main(scenario_id: str, details: bool, json_output: str | None) -> None:
    settings = Settings.from_env()
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
    ) as client:
        engine = RunEngine(
            settings,
            ParitokClient(settings, client),
            OpenAICompatibleClient(settings, client),
        )
        result = await engine.run(
            uuid.uuid4().hex,
            RunCreate(scenario_id=scenario_id),
        )
    metrics = result.metrics
    print(f"LIVE_SCENARIO_VALIDATION={result.validation.status}")
    print(f"LIVE_SCENARIO_FALLBACK={result.fallback or 'none'}")
    print(f"LIVE_SCENARIO_ATTEMPTS={len(result.attempts)}")
    print(f"LIVE_SCENARIO_ORIGINAL_TOKENS={metrics.original_input_tokens}")
    print(f"LIVE_SCENARIO_OPTIMIZED_TOKENS={metrics.optimized_input_tokens}")
    print(f"LIVE_SCENARIO_SAVED_TOKENS={metrics.total_tokens_saved}")
    print(f"LIVE_SCENARIO_SAVINGS_PERCENT={metrics.savings_percent}")
    print(f"LIVE_SCENARIO_LATENCY_MS={metrics.total_latency_ms}")
    if json_output:
        exported = result.model_dump(mode="json")
        exported["run_id"] = "redacted"
        Path(json_output).write_text(
            json.dumps(exported, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"LIVE_SCENARIO_JSON={json_output}")
    if details:
        if result.baseline:
            print(f"\nBASELINE_ANSWER:\n{result.baseline.text}")
        for attempt in result.attempts:
            print(
                f"\nATTEMPT level={attempt.level} "
                f"status={attempt.validation.status} "
                f"score={attempt.validation.score}"
            )
            for check in attempt.validation.checks:
                print(
                    f"CHECK passed={check['passed']} "
                    f"expected={check.get('expected_any', check.get('name'))}"
                )
            print(f"ANSWER:\n{attempt.answer.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_id", nargs="?", default="tool-output-anomaly")
    parser.add_argument("--details", action="store_true")
    parser.add_argument(
        "--json-output",
        help="Write a redacted JSON result suitable for examples and screenshot previews.",
    )
    arguments = parser.parse_args()
    asyncio.run(main(arguments.scenario_id, arguments.details, arguments.json_output))
