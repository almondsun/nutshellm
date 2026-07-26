from nutshellm.classifier import (
    classify,
    critical_spans,
    immutable_recall,
    safer_level,
)
from nutshellm.schemas import ContextSegment, SegmentDisposition, SegmentKind


def test_duplicate_segment_is_disposable():
    segment = ContextSegment(
        id="a",
        kind=SegmentKind.TOOL_RESULT,
        content="worker heartbeat ok " * 80,
    )
    seen: set[str] = set()
    first = classify(segment, seen, "gpt-4.1-mini")
    duplicate = classify(segment.model_copy(update={"id": "b"}), seen, "gpt-4.1-mini")
    assert first.disposition == SegmentDisposition.COMPRESSIBLE
    assert duplicate.disposition == SegmentDisposition.DISPOSABLE
    assert duplicate.reason == "exact duplicate"


def test_critical_span_recall_requires_exact_values():
    text = (
        'File "/app/worker.py", line 42, in run\n'
        "PoolTimeoutError: connection pool exhausted\n"
        "2026-07-23T14:37:00Z latency=1840ms"
    )
    spans = critical_spans(text)
    assert {span.kind for span in spans} >= {
        "stack_frame",
        "error",
        "timestamp",
        "measurement",
    }
    assert immutable_recall(spans, text) == 1
    assert immutable_recall(spans, "PoolTimeoutError only") < 1


def test_code_and_docs_use_one_safer_level():
    assert safer_level("L2", SegmentKind.FILE_READ) == "L1"
    assert safer_level("L1", SegmentKind.DOCUMENTATION) == "L0"
    assert safer_level("L2", SegmentKind.LOG_OUTPUT) == "L2"
