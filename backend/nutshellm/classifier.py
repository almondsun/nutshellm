"""Deterministic context classification and immutable-fact extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import ContextSegment, CriticalSpan, SegmentDisposition, SegmentKind
from .tokenizer import count_tokens

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("stack_frame", re.compile(r'File\s+"[^"]+",\s+line\s+\d+(?:,\s+in\s+\w+)?')),
    (
        "path",
        re.compile(
            r"(?<!\w)(?:/[\w.-]+)+(?:\.[A-Za-z0-9]+)?|"
            r"\b(?:src|app|lib|tests?)/[\w./-]+\.[A-Za-z0-9]+\b"
        ),
    ),
    (
        "signature",
        re.compile(r"\b(?:async\s+def|def|class)\s+[A-Za-z_]\w*\s*(?:\([^)\n]*\))?"),
    ),
    (
        "error",
        re.compile(
            r"\b[A-Z][A-Za-z]*(?:Error|Exception|Warning|Failure)\b"
            r"(?::\s*[^\n]{1,160})?"
        ),
    ),
    ("error_code", re.compile(r"\b(?:HTTP\s*)?[1-5]\d{2}\b|\b[A-Z][A-Z0-9_]{2,}_\d+\b")),
    (
        "timestamp",
        re.compile(
            r"\b\d{4}-\d{2}-\d{2}[T ][0-2]\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?Z?\b"
        ),
    ),
    (
        "measurement",
        re.compile(
            r"(?<![\w.])-?\d+(?:\.\d+)?\s*(?:ms|s|sec|%|MB|GB|KiB|MiB|GiB|"
            r"req/s|rps|rpm|°C)\b"
        ),
    ),
    ("url", re.compile(r"https?://[^\s'\"<>()]+")),
    (
        "identifier",
        re.compile(
            r"\b(?:[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}|"
            r"[a-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*)\b"
        ),
    ),
    ("quoted_literal", re.compile(r"(?P<q>['\"])[^'\"\n]{4,120}(?P=q)")),
)

_BOILERPLATE = ("generated file do not edit", "all rights reserved", "lorem ipsum")


@dataclass(frozen=True)
class Classification:
    disposition: SegmentDisposition
    reason: str
    critical_spans: list[CriticalSpan]


def normalize_for_duplicate(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def critical_spans(text: str) -> list[CriticalSpan]:
    found: list[tuple[int, int, CriticalSpan]] = []
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0).strip()
            if value:
                found.append((match.start(), match.end(), CriticalSpan(kind=kind, text=value)))
    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    result: list[CriticalSpan] = []
    occupied_until = -1
    seen: set[tuple[str, str]] = set()
    for start, end, span in found:
        key = (span.kind, span.text)
        if start < occupied_until or key in seen:
            continue
        result.append(span)
        occupied_until = end
        seen.add(key)
    return result


def classify(segment: ContextSegment, seen: set[str], model: str) -> Classification:
    normalized = normalize_for_duplicate(segment.content)
    spans = critical_spans(segment.content)
    if not normalized:
        return Classification(SegmentDisposition.DISPOSABLE, "empty content", spans)
    if normalized in seen:
        return Classification(SegmentDisposition.DISPOSABLE, "exact duplicate", spans)
    seen.add(normalized)
    if any(marker in normalized for marker in _BOILERPLATE) and count_tokens(
        segment.content, model
    ) < 256:
        return Classification(SegmentDisposition.DISPOSABLE, "known boilerplate", spans)
    tokens = count_tokens(segment.content, model)
    if tokens < 128:
        return Classification(
            SegmentDisposition.IMMUTABLE, "short context is safer to retain", spans
        )
    if segment.kind == SegmentKind.OTHER and any(
        span.kind == "stack_frame" for span in spans
    ):
        return Classification(
            SegmentDisposition.IMMUTABLE, "stack trace segment retained verbatim", spans
        )
    return Classification(
        SegmentDisposition.COMPRESSIBLE,
        "large typed context eligible for Paritok",
        spans,
    )


def immutable_recall(spans: list[CriticalSpan], candidate: str) -> float:
    if not spans:
        return 1.0
    kept = sum(1 for span in spans if span.text in candidate)
    return kept / len(spans)


def safer_level(requested: str, kind: SegmentKind) -> str:
    order = ("L0", "L1", "L2", "L3")
    index = order.index(requested)
    if kind in {SegmentKind.FILE_READ, SegmentKind.DOCUMENTATION} and index > 0:
        return order[index - 1]
    return requested
