from nutshellm.clients import CompressionResponse
from nutshellm.config import Settings
from nutshellm.orchestrator import RunEngine
from nutshellm.schemas import (
    ContextSegment,
    ModelAnswer,
    ModelUsage,
    RunCreate,
    RunMode,
    SegmentKind,
)


class FakeParitok:
    def __init__(self, replacement: str | None = None):
        self.replacement = replacement
        self.levels = []

    async def compress(self, content, task, kind, level):
        self.levels.append(level)
        if self.replacement is None:
            return CompressionResponse(content, False)
        return CompressionResponse(self.replacement, True)


class SequencedProvider:
    def __init__(self, answers):
        self.answers = iter(answers)

    async def complete(self, **_):
        return ModelAnswer(
            text=next(self.answers),
            usage=ModelUsage(input_tokens=1000, output_tokens=50),
        )

    async def judge(self, *_):
        return {"equivalent": True, "score": 1, "reason": "same"}, ModelUsage()


async def test_curated_failure_retries_at_safer_level():
    good = (
        "src/retries/cache.py key_for omits attempt from the cache key and uses "
        "only request_id; include attempt in the key."
    )
    provider = SequencedProvider([good, "insufficient", good])
    paritok = FakeParitok()
    engine = RunEngine(Settings(), paritok, provider)
    result = await engine.run(
        "run1",
        RunCreate(scenario_id="retry-cache-bug", mode=RunMode.COMPARE),
    )
    assert [attempt.level for attempt in result.attempts] == ["L2", "L1"]
    assert result.validation.status == "passed"
    assert result.fallback is None


async def test_missing_critical_span_restores_segment_before_model():
    original = (
        "2026-07-23T14:37:00Z PoolTimeoutError: connection pool exhausted "
        "latency=1840ms " + "normal telemetry " * 100
    )
    provider = SequencedProvider(["custom answer"])
    engine = RunEngine(
        Settings(),
        FakeParitok("short summary without exact facts"),
        provider,
    )
    result = await engine.run(
        "run2",
        RunCreate(
            task="What happened?",
            segments=[
                ContextSegment(
                    id="logs", kind=SegmentKind.LOG_OUTPUT, content=original
                )
            ],
            mode=RunMode.OPTIMIZE,
        ),
    )
    decision = result.final_segments[0]
    assert decision.restored
    assert decision.optimized == original
    assert decision.immutable_recall < 1
