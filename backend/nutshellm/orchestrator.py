"""End-to-end baseline, optimization, validation, and fallback orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .classifier import classify, immutable_recall, safer_level
from .clients import OpenAICompatibleClient, ParitokClient
from .config import Settings
from .scenarios import Scenario, get_scenario
from .schemas import (
    AttemptResult,
    ContextSegment,
    ModelAnswer,
    ModelUsage,
    RunCreate,
    RunMode,
    RunResult,
    SavingsMetrics,
    SegmentDecision,
    SegmentDisposition,
    ValidationResult,
)
from .tokenizer import count_tokens
from .validators import (
    validate_curated,
    validate_unjudged,
    validation_from_judge,
)

_SYSTEM_PROMPT = (
    "You are an evidence-grounded technical analyst. Use only the supplied context. "
    "Preserve exact identifiers, paths, timestamps, measurements, and error messages. "
    "If evidence is missing, say so explicitly. "
)


@dataclass
class PreparedRun:
    scenario: Scenario | None
    task: str
    segments: list[ContextSegment]
    mode: RunMode


class RunEngine:
    def __init__(
        self,
        settings: Settings,
        paritok: ParitokClient,
        provider: OpenAICompatibleClient,
    ):
        self.settings = settings
        self.paritok = paritok
        self.provider = provider

    def prepare(self, request: RunCreate) -> PreparedRun:
        if request.scenario_id:
            scenario = get_scenario(request.scenario_id)
            if scenario is None:
                raise ValueError("unknown scenario")
            return PreparedRun(
                scenario=scenario,
                task=scenario.task,
                segments=list(scenario.segments),
                mode=request.mode,
            )
        return PreparedRun(
            scenario=None,
            task=request.task or "",
            segments=list(request.segments or []),
            mode=request.mode,
        )

    async def run(self, run_id: str, request: RunCreate) -> RunResult:
        started = time.perf_counter()
        prepared = self.prepare(request)
        original_context = build_context(prepared.segments)
        system_prompt = _SYSTEM_PROMPT + (
            prepared.scenario.answer_hint if prepared.scenario else "Answer the task concisely."
        )

        baseline: ModelAnswer | None = None
        task_usage = ModelUsage()
        if prepared.mode == RunMode.COMPARE:
            baseline = await self.provider.complete(
                task=prepared.task,
                context=original_context,
                system_prompt=system_prompt,
            )
            task_usage = add_usage(task_usage, baseline.usage)

        attempts: list[AttemptResult] = []
        evaluation_usage = ModelUsage()
        selected: AttemptResult | None = None

        for level in ("L2", "L1", "L0"):
            decisions, compression_ms = await self._optimize(
                prepared.task, prepared.segments, level
            )
            optimized_context = build_decision_context(decisions)
            answer = await self.provider.complete(
                task=prepared.task,
                context=optimized_context,
                system_prompt=system_prompt,
            )
            task_usage = add_usage(task_usage, answer.usage)
            validation, judge_usage = await self._validate(
                prepared, answer, baseline
            )
            evaluation_usage = add_usage(evaluation_usage, judge_usage)
            attempt = AttemptResult(
                level=level,
                segments=decisions,
                answer=answer,
                validation=validation,
                context_tokens=count_tokens(
                    optimized_context, self.settings.task_model
                ),
                compression_latency_ms=compression_ms,
            )
            attempts.append(attempt)
            if validation.status in {"passed", "unverified"}:
                selected = attempt
                break

        fallback: str | None = None
        if selected is None:
            fallback = "original_context"
            if baseline is None:
                baseline = await self.provider.complete(
                    task=prepared.task,
                    context=original_context,
                    system_prompt=system_prompt,
                )
                task_usage = add_usage(task_usage, baseline.usage)
            selected = AttemptResult(
                level="original",
                segments=original_decisions(prepared.segments, self.settings.task_model),
                answer=baseline,
                validation=(
                    validate_curated(baseline.text, prepared.scenario)
                    if prepared.scenario
                    else validate_unjudged()
                ),
                context_tokens=count_tokens(original_context, self.settings.task_model),
                compression_latency_ms=0,
            )
            attempts.append(selected)

        metrics = self._metrics(
            baseline=baseline,
            selected=selected,
            original_context=original_context,
            task=prepared.task,
            system_prompt=system_prompt,
            evaluation_usage=evaluation_usage,
            task_usage=task_usage,
            total_latency_ms=round((time.perf_counter() - started) * 1000),
        )
        return RunResult(
            run_id=run_id,
            scenario_id=prepared.scenario.id if prepared.scenario else None,
            mode=prepared.mode,
            task=prepared.task,
            baseline=baseline if prepared.mode == RunMode.COMPARE else None,
            optimized=selected.answer,
            final_segments=selected.segments,
            attempts=attempts,
            validation=selected.validation,
            fallback=fallback,
            metrics=metrics,
        )

    async def _optimize(
        self, task: str, segments: list[ContextSegment], requested_level: str
    ) -> tuple[list[SegmentDecision], int]:
        started = time.perf_counter()
        seen: set[str] = set()
        decisions: list[SegmentDecision] = []
        for segment in segments:
            original_tokens = count_tokens(segment.content, self.settings.task_model)
            classification = classify(segment, seen, self.settings.task_model)
            if classification.disposition == SegmentDisposition.DISPOSABLE:
                decisions.append(
                    SegmentDecision(
                        id=segment.id,
                        kind=segment.kind,
                        disposition=classification.disposition,
                        reason=classification.reason,
                        original=segment.content,
                        optimized="",
                        original_tokens=original_tokens,
                        optimized_tokens=0,
                        critical_spans=classification.critical_spans,
                    )
                )
                continue
            if classification.disposition == SegmentDisposition.IMMUTABLE:
                decisions.append(
                    SegmentDecision(
                        id=segment.id,
                        kind=segment.kind,
                        disposition=classification.disposition,
                        reason=classification.reason,
                        original=segment.content,
                        optimized=segment.content,
                        original_tokens=original_tokens,
                        optimized_tokens=original_tokens,
                        critical_spans=classification.critical_spans,
                    )
                )
                continue

            level = safer_level(requested_level, segment.kind)
            compressed = await self.paritok.compress(
                segment.content, task, segment.kind.value, level
            )
            recall = immutable_recall(
                classification.critical_spans, compressed.compressed
            )
            restored = compressed.applied and recall < 1.0
            optimized = segment.content if restored else compressed.compressed
            decisions.append(
                SegmentDecision(
                    id=segment.id,
                    kind=segment.kind,
                    disposition=classification.disposition,
                    reason=(
                        "restored because a critical span changed"
                        if restored
                        else classification.reason
                    ),
                    original=segment.content,
                    optimized=optimized,
                    level=level,
                    original_tokens=original_tokens,
                    optimized_tokens=count_tokens(
                        optimized, self.settings.task_model
                    ),
                    critical_spans=classification.critical_spans,
                    immutable_recall=recall,
                    paritok_applied=compressed.applied and not restored,
                    restored=restored,
                )
            )
        return decisions, round((time.perf_counter() - started) * 1000)

    async def _validate(
        self,
        prepared: PreparedRun,
        answer: ModelAnswer,
        baseline: ModelAnswer | None,
    ) -> tuple[ValidationResult, ModelUsage]:
        if prepared.scenario:
            return validate_curated(answer.text, prepared.scenario), ModelUsage()
        if (
            self.settings.enable_llm_judge
            and prepared.mode == RunMode.COMPARE
            and baseline is not None
        ):
            judged, usage = await self.provider.judge(
                prepared.task, baseline.text, answer.text
            )
            return validation_from_judge(judged, usage)
        return validate_unjudged(), ModelUsage()

    def _metrics(
        self,
        *,
        baseline: ModelAnswer | None,
        selected: AttemptResult,
        original_context: str,
        task: str,
        system_prompt: str,
        evaluation_usage: ModelUsage,
        task_usage: ModelUsage,
        total_latency_ms: int,
    ) -> SavingsMetrics:
        original_input = (
            baseline.usage.input_tokens
            if baseline
            else count_tokens(
                original_context + task + system_prompt, self.settings.task_model
            )
        )
        optimized_input = selected.answer.usage.input_tokens
        total_saved = original_input - optimized_input
        paritok_saved = sum(
            max(0, decision.original_tokens - decision.optimized_tokens)
            for decision in selected.segments
            if decision.paritok_applied
        )
        pruned = sum(
            decision.original_tokens
            for decision in selected.segments
            if decision.disposition == SegmentDisposition.DISPOSABLE
        )
        saved_cost = (
            total_saved * self.settings.task_input_usd_per_mtok / 1_000_000
        )
        evaluation_tokens = (
            evaluation_usage.input_tokens + evaluation_usage.output_tokens
        )
        evaluation_cost = (
            evaluation_usage.input_tokens
            * self.settings.task_input_usd_per_mtok
            / 1_000_000
            + evaluation_usage.output_tokens
            * self.settings.task_output_usd_per_mtok
            / 1_000_000
        )
        total_run_cost = (
            (task_usage.input_tokens + evaluation_usage.input_tokens)
            * self.settings.task_input_usd_per_mtok
            / 1_000_000
            + (task_usage.output_tokens + evaluation_usage.output_tokens)
            * self.settings.task_output_usd_per_mtok
            / 1_000_000
        )
        return SavingsMetrics(
            original_input_tokens=original_input,
            optimized_input_tokens=optimized_input,
            paritok_tokens_saved=paritok_saved,
            directly_pruned_tokens=pruned,
            total_tokens_saved=total_saved,
            savings_percent=round(
                total_saved / original_input * 100, 2
            )
            if original_input
            else 0,
            estimated_input_cost_saved_usd=round(saved_cost, 6),
            evaluation_overhead_tokens=evaluation_tokens,
            evaluation_overhead_cost_usd=round(evaluation_cost, 6),
            estimated_total_run_cost_usd=round(total_run_cost, 6),
            total_latency_ms=total_latency_ms,
        )


def build_context(segments: list[ContextSegment]) -> str:
    return "\n\n".join(
        _format_segment(segment.id, segment.kind.value, segment.source, segment.content)
        for segment in segments
    )


def build_decision_context(decisions: list[SegmentDecision]) -> str:
    return "\n\n".join(
        _format_segment(decision.id, decision.kind.value, None, decision.optimized)
        for decision in decisions
        if decision.disposition != SegmentDisposition.DISPOSABLE
    )


def _format_segment(
    segment_id: str, kind: str, source: str | None, content: str
) -> str:
    source_label = f" source={source}" if source else ""
    return f"--- SEGMENT id={segment_id} kind={kind}{source_label} ---\n{content}"


def original_decisions(
    segments: list[ContextSegment], model: str
) -> list[SegmentDecision]:
    return [
        SegmentDecision(
            id=segment.id,
            kind=segment.kind,
            disposition=SegmentDisposition.IMMUTABLE,
            reason="original-context fallback",
            original=segment.content,
            optimized=segment.content,
            original_tokens=count_tokens(segment.content, model),
            optimized_tokens=count_tokens(segment.content, model),
            restored=True,
        )
        for segment in segments
    ]


def add_usage(left: ModelUsage, right: ModelUsage) -> ModelUsage:
    return ModelUsage(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        latency_ms=left.latency_ms + right.latency_ms,
        estimated=left.estimated or right.estimated,
    )
