"""Curated, deterministic scenarios used by the public workbench."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import ContextSegment, SegmentKind


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    category: str
    description: str
    task: str
    segments: tuple[ContextSegment, ...]
    required_groups: tuple[tuple[str, ...], ...]
    answer_hint: str

    def public(self) -> dict[str, str | int]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "segment_count": len(self.segments),
        }


_NOISE = "\n".join(
    f"DEBUG worker={index % 4} heartbeat ok queue_depth=0 retry_count=0"
    for index in range(42)
)
_METRIC_NOISE = "\n".join(
    f"2026-07-23T14:{minute:02d}:00Z INFO api latency=118ms error_rate=0.2% requests=840"
    for minute in range(35)
)

SCENARIOS: dict[str, Scenario] = {
    "retry-cache-bug": Scenario(
        id="retry-cache-bug",
        title="Find a retry-cache bug",
        category="Code debugging",
        description="Preserve an exact function contract while compressing source and test noise.",
        task=(
            "Identify the root cause of the stale retry result and name the file, function, "
            "and minimal fix. Do not invent details."
        ),
        segments=(
            ContextSegment(
                id="cache-source",
                kind=SegmentKind.FILE_READ,
                source="src/retries/cache.py",
                content=(
                    "src/retries/cache.py\n"
                    "class RetryCache:\n"
                    "    def key_for(self, request_id: str, attempt: int) -> str:\n"
                    "        return request_id\n\n"
                    "    def get_or_create(self, request_id: str, attempt: int, factory):\n"
                    "        key = self.key_for(request_id, attempt)\n"
                    "        if key not in self._values:\n"
                    "            self._values[key] = factory()\n"
                    "        return self._values[key]\n\n"
                    + "\n".join(
                        f"def unrelated_helper_{i}(value):\n    return value"
                        for i in range(26)
                    )
                ),
            ),
            ContextSegment(
                id="failing-test",
                kind=SegmentKind.TOOL_RESULT,
                content=(
                    "tests/retries/test_cache.py::test_attempts_are_isolated FAILED\n"
                    "AssertionError: expected result for attempt 2, received cached result "
                    "for attempt 1\n"
                    "request_id='req_7f91' attempt=2\n" + _NOISE
                ),
            ),
        ),
        required_groups=(
            ("src/retries/cache.py",),
            ("key_for",),
            ("attempt", "cache key"),
            ("request_id",),
        ),
        answer_hint=(
            "Answer concisely with root cause, exact file and symbol, and minimal fix."
        ),
    ),
    "checkout-incident": Scenario(
        id="checkout-incident",
        title="Diagnose a checkout incident",
        category="Incident response",
        description="Keep the spike, timestamp, error, and causal deployment amid repetitive telemetry.",
        task=(
            "State the affected service, start time, peak error rate, exact error, and most "
            "likely trigger. Use only the supplied evidence."
        ),
        segments=(
            ContextSegment(
                id="metrics",
                kind=SegmentKind.LOG_OUTPUT,
                content=(
                    _METRIC_NOISE
                    + "\n2026-07-23T14:37:00Z ALERT checkout-api latency=1840ms "
                    "error_rate=18.7% requests=912\n"
                    "2026-07-23T14:38:00Z ERROR checkout-api "
                    "PoolTimeoutError: connection pool exhausted\n"
                    "2026-07-23T14:39:00Z ERROR checkout-api error_rate=21.4% latency=2230ms\n"
                ),
            ),
            ContextSegment(
                id="deploy",
                kind=SegmentKind.TOOL_RESULT,
                content=(
                    "Deployment event\nservice=checkout-api\n"
                    "version=payments-client-3.8.0\nstarted=2026-07-23T14:35:12Z\n"
                    "change=default pool_size reduced from 80 to 8\nstatus=completed\n"
                    + _NOISE
                ),
            ),
        ),
        required_groups=(
            ("checkout-api",),
            ("2026-07-23T14:37:00Z", "14:37"),
            ("21.4%",),
            ("PoolTimeoutError", "connection pool exhausted"),
            ("payments-client-3.8.0", "80 to 8", "pool_size"),
        ),
        answer_hint="Return a five-part evidence-grounded incident summary.",
    ),
    "tool-output-anomaly": Scenario(
        id="tool-output-anomaly",
        title="Extract the anomalous worker",
        category="Tool-output analysis",
        description="Remove duplicated health output without losing the lone failure.",
        task=(
            "Which worker is unhealthy, what exact condition failed, and what action should "
            "be taken first?"
        ),
        segments=(
            ContextSegment(
                id="health-primary",
                kind=SegmentKind.TOOL_RESULT,
                content=(
                    _NOISE
                    + "\nERROR worker=worker-17 disk_free=1.8% "
                    "DiskPressureWarning: minimum 5% required\n"
                    "ACTION_HINT drain worker-17 before cleanup\n"
                    + _NOISE
                ),
            ),
            ContextSegment(
                id="health-duplicate",
                kind=SegmentKind.TOOL_RESULT,
                content=_NOISE,
            ),
            ContextSegment(
                id="health-duplicate-2",
                kind=SegmentKind.TOOL_RESULT,
                content=_NOISE,
            ),
        ),
        required_groups=(
            ("worker-17",),
            ("1.8%",),
            ("DiskPressureWarning", "minimum 5%"),
            ("drain",),
        ),
        answer_hint="Answer with worker, failed threshold, and first action.",
    ),
}


def list_scenarios() -> list[dict[str, str | int]]:
    return [scenario.public() for scenario in SCENARIOS.values()]


def get_scenario(scenario_id: str) -> Scenario | None:
    return SCENARIOS.get(scenario_id)
