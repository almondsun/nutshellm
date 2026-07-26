"""FastAPI routes and application lifecycle."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .clients import ExternalServiceError, OpenAICompatibleClient, ParitokClient
from .config import Settings
from .orchestrator import RunEngine
from .scenarios import get_scenario, list_scenarios
from .schemas import JobStatus, RunCreate
from .security import (
    SESSION_COOKIE,
    client_ip,
    identity_key,
    new_session,
    parse_session,
    verify_turnstile,
)
from .storage import Store

logger = logging.getLogger("nutshellm")


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(
                    status_code=400, content={"detail": "invalid content length"}
                )(scope, receive, send)
                return

        messages: list[Message] = []
        total = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                return
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        await JSONResponse(
            status_code=413, content={"detail": "request body too large"}
        )(scope, receive, send)


def create_app(
    settings: Settings | None = None,
    *,
    http_client: httpx.AsyncClient | None = None,
    engine: RunEngine | None = None,
) -> FastAPI:
    cfg = settings or Settings.from_env()
    production_errors = cfg.validate_production()
    if production_errors:
        raise RuntimeError(
            "Invalid production configuration: " + "; ".join(production_errors)
        )
    cfg.ensure_runtime_paths()
    store = Store(cfg.database_path)
    store.initialize()
    owns_http = http_client is None
    shared_http = http_client or httpx.AsyncClient(
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    )
    run_engine = engine or RunEngine(
        cfg,
        ParitokClient(cfg, shared_http),
        OpenAICompatibleClient(cfg, shared_http),
    )
    stop_event = asyncio.Event()

    async def worker() -> None:
        while not stop_event.is_set():
            claimed = await asyncio.to_thread(store.claim_next)
            if claimed is None:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=0.25)
                except TimeoutError:
                    continue
                continue
            job_id, payload, expires_at = claimed
            try:
                request = RunCreate.model_validate(payload)
                remaining = (
                    datetime.fromisoformat(expires_at) - datetime.now(UTC)
                ).total_seconds()
                if remaining <= 0:
                    await asyncio.to_thread(store.fail, job_id, "run expired")
                    continue
                async with asyncio.timeout(remaining):
                    result = await run_engine.run(job_id, request)
                await asyncio.to_thread(
                    store.complete,
                    job_id,
                    result.model_dump(mode="json"),
                    cfg.result_ttl_seconds,
                )
            except TimeoutError:
                await asyncio.to_thread(store.fail, job_id, "run expired")
            except (ExternalServiceError, ValueError) as exc:
                await asyncio.to_thread(store.fail, job_id, str(exc))
            except Exception:
                logger.exception("Unexpected run failure for job %s", job_id)
                await asyncio.to_thread(store.fail, job_id, "internal run failure")

    async def janitor() -> None:
        while not stop_event.is_set():
            await asyncio.to_thread(store.purge_expired)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=30)
            except TimeoutError:
                continue

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        workers = [
            asyncio.create_task(worker(), name="run-worker"),
            asyncio.create_task(janitor(), name="retention-janitor"),
        ]
        yield
        stop_event.set()
        await asyncio.gather(*workers, return_exceptions=True)
        if owns_http:
            await shared_http.aclose()

    app = FastAPI(
        title="nutsheLLM API",
        version="0.1.0",
        docs_url="/api/docs" if not cfg.production else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = cfg
    app.state.store = store
    app.add_middleware(
        BodySizeLimitMiddleware, max_bytes=cfg.max_context_chars * 4 + 32_000
    )

    @app.middleware("http")
    async def secure_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self' https://challenges.cloudflare.com; "
            "frame-src https://challenges.cloudflare.com; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
        return response

    @app.get("/api/v1/scenarios")
    async def scenarios() -> list[dict]:
        return list_scenarios()

    @app.get("/api/v1/public-config")
    async def public_config() -> dict[str, str]:
        return {"turnstile_site_key": cfg.turnstile_site_key}

    @app.post("/api/v1/runs", status_code=status.HTTP_202_ACCEPTED)
    async def create_run(
        body: RunCreate, request: Request, response: Response
    ) -> dict[str, str]:
        _validate_limits(body, cfg)
        if body.scenario_id and get_scenario(body.scenario_id) is None:
            raise HTTPException(status_code=404, detail="scenario not found")
        ip = client_ip(request, cfg.trusted_proxy_cidrs)
        session_id = parse_session(
            request.cookies.get(SESSION_COOKIE), cfg.session_signing_secret
        )
        if session_id is None:
            session_id, signed = new_session(cfg.session_signing_secret)
            response.set_cookie(
                SESSION_COOKIE,
                signed,
                httponly=True,
                secure=cfg.production,
                samesite="strict",
                max_age=86_400,
            )
        if cfg.production and not await verify_turnstile(
            body.turnstile_token, ip, cfg, shared_http
        ):
            raise HTTPException(status_code=403, detail="human verification failed")
        allowed, reason = await asyncio.to_thread(
            store.consume_quota,
            (
                identity_key("ip", ip, cfg.session_signing_secret),
                identity_key("session", session_id, cfg.session_signing_secret),
            ),
            cfg.per_ip_daily_run_limit,
            cfg.global_daily_run_limit,
            cfg.global_daily_budget_usd,
            cfg.run_budget_reservation_usd(),
        )
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)
        job_id = uuid.uuid4().hex
        owner = identity_key("owner", session_id, cfg.session_signing_secret)
        payload = body.model_dump(mode="json", exclude={"turnstile_token"})
        times = await asyncio.to_thread(
            store.enqueue, job_id, owner, payload, cfg.result_ttl_seconds
        )
        return {
            "id": job_id,
            "status": "queued",
            "status_url": f"/api/v1/runs/{job_id}",
            **times,
        }

    @app.get("/api/v1/runs/{job_id}", response_model=JobStatus)
    async def get_run(job_id: str, request: Request) -> dict:
        if len(job_id) != 32 or any(char not in "0123456789abcdef" for char in job_id):
            raise HTTPException(status_code=404, detail="run not found")
        session_id = parse_session(
            request.cookies.get(SESSION_COOKIE), cfg.session_signing_secret
        )
        if session_id is None:
            raise HTTPException(status_code=404, detail="run not found or expired")
        owner = identity_key(
            "owner", session_id, cfg.session_signing_secret
        )
        job = await asyncio.to_thread(store.get_job, job_id, owner)
        if job is None:
            raise HTTPException(status_code=404, detail="run not found or expired")
        return job

    @app.get("/api/v1/metrics/summary")
    async def metrics() -> dict:
        return await asyncio.to_thread(store.aggregate)

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def ready() -> Response:
        errors = cfg.validate_production()
        if errors:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reasons": errors},
            )
        return JSONResponse({"status": "ready"})

    frontend = Path(os.getenv("FRONTEND_DIST", "frontend/dist")).resolve()
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")

    return app


def _validate_limits(body: RunCreate, settings: Settings) -> None:
    if body.scenario_id:
        return
    task = body.task or ""
    segments = body.segments or []
    if len(task) > settings.max_task_chars:
        raise HTTPException(status_code=413, detail="task exceeds size limit")
    if len(segments) > settings.max_segments:
        raise HTTPException(status_code=413, detail="too many context segments")
    if sum(len(segment.content) for segment in segments) > settings.max_context_chars:
        raise HTTPException(status_code=413, detail="context exceeds size limit")
