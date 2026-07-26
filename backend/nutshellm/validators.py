"""Deterministic and optional semantic task-quality validators."""

from __future__ import annotations

from .scenarios import Scenario
from .schemas import ModelUsage, ValidationResult


def validate_curated(answer: str, scenario: Scenario) -> ValidationResult:
    folded = answer.casefold()
    checks = []
    for alternatives in scenario.required_groups:
        matched = any(value.casefold() in folded for value in alternatives)
        checks.append(
            {
                "name": "required fact",
                "expected_any": list(alternatives),
                "passed": matched,
            }
        )
    passed = all(check["passed"] for check in checks)
    return ValidationResult(
        status="passed" if passed else "failed",
        score=sum(bool(check["passed"]) for check in checks) / len(checks),
        checks=checks,
        reason="all required facts preserved" if passed else "one or more required facts missing",
    )


def validate_unjudged() -> ValidationResult:
    return ValidationResult(
        status="unverified",
        score=None,
        reason="no deterministic validator is available for custom input",
    )


def validation_from_judge(
    result: dict, usage: ModelUsage
) -> tuple[ValidationResult, ModelUsage]:
    equivalent = result.get("equivalent") is True
    try:
        score = float(result.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(score, 1.0))
    return (
        ValidationResult(
            status="passed" if equivalent and score >= 0.8 else "failed",
            score=score,
            checks=[{"name": "blind semantic judge", "passed": equivalent}],
            reason=str(result.get("reason", ""))[:500],
        ),
        usage,
    )
