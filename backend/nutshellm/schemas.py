"""Validated API and domain schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SegmentKind(StrEnum):
    FILE_READ = "file_read"
    LOG_OUTPUT = "log_output"
    TOOL_RESULT = "tool_result"
    HISTORY = "history"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class SegmentDisposition(StrEnum):
    IMMUTABLE = "immutable"
    COMPRESSIBLE = "compressible"
    DISPOSABLE = "disposable"


class RunMode(StrEnum):
    COMPARE = "compare"
    OPTIMIZE = "optimize"


class ContextSegment(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    kind: SegmentKind
    content: str = Field(min_length=1, max_length=50_000)
    source: str | None = Field(default=None, max_length=500)


class RunCreate(BaseModel):
    scenario_id: str | None = Field(default=None, max_length=80)
    task: str | None = Field(default=None, max_length=4_000)
    segments: list[ContextSegment] | None = Field(default=None, max_length=12)
    mode: RunMode = RunMode.COMPARE
    turnstile_token: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def validate_source(self) -> "RunCreate":
        if self.scenario_id and (self.task or self.segments):
            raise ValueError("scenario_id cannot be combined with custom task/segments")
        if not self.scenario_id and (not self.task or not self.segments):
            raise ValueError("provide scenario_id or both task and segments")
        ids = [segment.id for segment in self.segments or []]
        if len(ids) != len(set(ids)):
            raise ValueError("segment ids must be unique")
        return self


class CriticalSpan(BaseModel):
    kind: str
    text: str


class SegmentDecision(BaseModel):
    id: str
    kind: SegmentKind
    disposition: SegmentDisposition
    reason: str
    original: str
    optimized: str
    level: str | None = None
    original_tokens: int
    optimized_tokens: int
    critical_spans: list[CriticalSpan] = Field(default_factory=list)
    immutable_recall: float = 1.0
    paritok_applied: bool = False
    restored: bool = False


class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    estimated: bool = False


class ModelAnswer(BaseModel):
    text: str
    usage: ModelUsage


class ValidationResult(BaseModel):
    status: Literal["passed", "failed", "unverified", "inconclusive"]
    score: float | None = None
    checks: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = ""


class AttemptResult(BaseModel):
    level: str
    segments: list[SegmentDecision]
    answer: ModelAnswer
    validation: ValidationResult
    context_tokens: int
    compression_latency_ms: int


class SavingsMetrics(BaseModel):
    original_input_tokens: int
    optimized_input_tokens: int
    paritok_tokens_saved: int
    directly_pruned_tokens: int
    total_tokens_saved: int
    savings_percent: float
    estimated_input_cost_saved_usd: float
    evaluation_overhead_tokens: int = 0
    evaluation_overhead_cost_usd: float = 0.0
    estimated_total_run_cost_usd: float = 0.0
    total_latency_ms: int


class RunResult(BaseModel):
    run_id: str
    scenario_id: str | None
    mode: RunMode
    task: str
    baseline: ModelAnswer | None
    optimized: ModelAnswer
    final_segments: list[SegmentDecision]
    attempts: list[AttemptResult]
    validation: ValidationResult
    fallback: str | None
    metrics: SavingsMetrics


class JobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "complete", "failed"]
    created_at: str
    expires_at: str
    result: RunResult | None = None
    error: str | None = None
