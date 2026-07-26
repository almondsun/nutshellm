"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _csv(name: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, "").split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    database_path: str = "data/nutshellm.sqlite3"
    result_ttl_seconds: int = 3600
    paritok_api_key: str = ""
    paritok_base_url: str = "https://www.paritok.com/api"
    paritok_model: str = "paritok-4b-v1"
    paritok_timeout_seconds: float = 90.0
    task_model_api_key: str = ""
    task_model_base_url: str = "https://api.openai.com/v1"
    task_model: str = "gpt-4.1-mini"
    task_max_output_tokens: int = 1200
    task_reasoning_effort: str = ""
    task_model_max_retries: int = 1
    task_model_retry_max_delay_seconds: float = 35.0
    judge_model: str = ""
    enable_llm_judge: bool = False
    task_input_usd_per_mtok: float = 0.0
    task_output_usd_per_mtok: float = 0.0
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""
    turnstile_expected_hostnames: tuple[str, ...] = ()
    session_signing_secret: str = "replace-me-in-production"
    per_ip_daily_run_limit: int = 5
    global_daily_run_limit: int = 100
    global_daily_budget_usd: float = 10.0
    max_task_chars: int = 4000
    max_segments: int = 12
    max_context_chars: int = 50_000
    trusted_proxy_cidrs: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            database_path=os.getenv("DATABASE_PATH", "data/nutshellm.sqlite3"),
            result_ttl_seconds=_int("RESULT_TTL_SECONDS", 3600),
            paritok_api_key=os.getenv("PARITOK_API_KEY", ""),
            paritok_base_url=os.getenv(
                "PARITOK_BASE_URL", "https://www.paritok.com/api"
            ).rstrip("/"),
            paritok_model=os.getenv("PARITOK_MODEL", "paritok-4b-v1"),
            paritok_timeout_seconds=_float("PARITOK_TIMEOUT_SECONDS", 90.0),
            task_model_api_key=os.getenv("TASK_MODEL_API_KEY", ""),
            task_model_base_url=os.getenv(
                "TASK_MODEL_BASE_URL", "https://api.openai.com/v1"
            ).rstrip("/"),
            task_model=os.getenv("TASK_MODEL", "gpt-4.1-mini"),
            task_max_output_tokens=_int("TASK_MAX_OUTPUT_TOKENS", 1200),
            task_reasoning_effort=os.getenv("TASK_REASONING_EFFORT", "").lower(),
            task_model_max_retries=_int("TASK_MODEL_MAX_RETRIES", 1),
            task_model_retry_max_delay_seconds=_float(
                "TASK_MODEL_RETRY_MAX_DELAY_SECONDS", 35.0
            ),
            judge_model=os.getenv("JUDGE_MODEL", ""),
            enable_llm_judge=_bool("ENABLE_LLM_JUDGE"),
            task_input_usd_per_mtok=_float("TASK_INPUT_USD_PER_MTOK", 0.0),
            task_output_usd_per_mtok=_float("TASK_OUTPUT_USD_PER_MTOK", 0.0),
            turnstile_site_key=os.getenv("TURNSTILE_SITE_KEY", ""),
            turnstile_secret_key=os.getenv("TURNSTILE_SECRET_KEY", ""),
            turnstile_expected_hostnames=_csv("TURNSTILE_EXPECTED_HOSTNAMES"),
            session_signing_secret=os.getenv(
                "SESSION_SIGNING_SECRET", "replace-me-in-production"
            ),
            per_ip_daily_run_limit=_int("PER_IP_DAILY_RUN_LIMIT", 5),
            global_daily_run_limit=_int("GLOBAL_DAILY_RUN_LIMIT", 100),
            global_daily_budget_usd=_float("GLOBAL_DAILY_BUDGET_USD", 10.0),
            max_task_chars=_int("MAX_TASK_CHARS", 4000),
            max_segments=_int("MAX_SEGMENTS", 12),
            max_context_chars=_int("MAX_CONTEXT_CHARS", 50_000),
            trusted_proxy_cidrs=_csv("TRUSTED_PROXY_CIDRS"),
        )

    @property
    def production(self) -> bool:
        return self.environment.lower() == "production"

    def ensure_runtime_paths(self) -> None:
        Path(self.database_path).expanduser().resolve().parent.mkdir(
            parents=True, exist_ok=True
        )

    def validate_production(self) -> list[str]:
        errors: list[str] = []
        if not self.production:
            return errors
        if not self.paritok_api_key:
            errors.append("PARITOK_API_KEY is required")
        if not self.task_model_api_key:
            errors.append("TASK_MODEL_API_KEY is required")
        if not self.turnstile_secret_key:
            errors.append("TURNSTILE_SECRET_KEY is required")
        if not self.turnstile_site_key:
            errors.append("TURNSTILE_SITE_KEY is required")
        if not self.turnstile_expected_hostnames:
            errors.append("TURNSTILE_EXPECTED_HOSTNAMES is required")
        if self.task_input_usd_per_mtok <= 0:
            errors.append("TASK_INPUT_USD_PER_MTOK must be configured")
        if self.task_output_usd_per_mtok <= 0:
            errors.append("TASK_OUTPUT_USD_PER_MTOK must be configured")
        if self.task_reasoning_effort not in {
            "",
            "none",
            "minimal",
            "low",
            "medium",
            "high",
        }:
            errors.append("TASK_REASONING_EFFORT is invalid")
        if self.session_signing_secret == "replace-me-in-production":
            errors.append("SESSION_SIGNING_SECRET must be replaced")
        return errors

    def run_budget_reservation_usd(self) -> float:
        """Conservative maximum reserved before a run's actual usage exists."""
        context_tokens = (
            self.max_context_chars + self.max_task_chars + 4_000
        ) // 4
        calls = 7 if self.enable_llm_judge else 4
        input_tokens = context_tokens + 2 * self.task_max_output_tokens
        per_call = (
            input_tokens * self.task_input_usd_per_mtok
            + self.task_max_output_tokens * self.task_output_usd_per_mtok
        ) / 1_000_000
        return calls * per_call
