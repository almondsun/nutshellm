"""Serve the workbench locally with a previously recorded curated result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn
from nutshellm.api import create_app
from nutshellm.config import Settings
from nutshellm.schemas import RunResult


class RecordedEngine:
    def __init__(self, result: RunResult):
        self.result = result

    async def run(self, run_id, request):
        return self.result.model_copy(
            update={"run_id": run_id, "scenario_id": request.scenario_id}
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("result_json")
    parser.add_argument("--port", type=int, default=8012)
    arguments = parser.parse_args()
    result = RunResult.model_validate(
        json.loads(Path(arguments.result_json).read_text(encoding="utf-8"))
    )
    settings = Settings(
        database_path="/tmp/nutshellm-screenshot-preview.sqlite3",
        per_ip_daily_run_limit=100,
        global_daily_run_limit=100,
    )
    uvicorn.run(
        create_app(settings, engine=RecordedEngine(result)),
        host="127.0.0.1",
        port=arguments.port,
    )


if __name__ == "__main__":
    main()
