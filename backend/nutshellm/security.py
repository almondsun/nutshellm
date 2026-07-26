"""Public-demo anti-abuse and anonymous-session helpers."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets

import httpx
from fastapi import Request

from .config import Settings

SESSION_COOKIE = "nutshellm_session"
TURNSTILE_ACTION = "nutshellm_run"


def sign_session(session_id: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode(), session_id.encode(), hashlib.sha256
    ).hexdigest()
    return f"{session_id}.{signature}"


def parse_session(value: str | None, secret: str) -> str | None:
    if not value or "." not in value:
        return None
    session_id, signature = value.rsplit(".", 1)
    expected = sign_session(session_id, secret).rsplit(".", 1)[1]
    if not hmac.compare_digest(signature, expected):
        return None
    return session_id


def new_session(secret: str) -> tuple[str, str]:
    session_id = secrets.token_urlsafe(24)
    return session_id, sign_session(session_id, secret)


def client_ip(request: Request, trusted_proxy_cidrs: tuple[str, ...]) -> str:
    raw = request.client.host if request.client else "0.0.0.0"
    try:
        peer = ipaddress.ip_address(raw)
        trusted = any(
            peer in ipaddress.ip_network(cidr, strict=False)
            for cidr in trusted_proxy_cidrs
        )
    except ValueError:
        trusted = False
    if trusted:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            raw = forwarded.split(",", 1)[0].strip()
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return "0.0.0.0"


def identity_key(namespace: str, value: str, secret: str) -> str:
    return hmac.new(
        secret.encode(), f"{namespace}|{value}".encode(), hashlib.sha256
    ).hexdigest()


async def verify_turnstile(
    token: str | None,
    remote_ip: str,
    settings: Settings,
    http_client: httpx.AsyncClient,
) -> bool:
    if not settings.production and not settings.turnstile_secret_key:
        return True
    if not settings.turnstile_secret_key or not token:
        return False
    try:
        response = await http_client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": settings.turnstile_secret_key,
                "response": token,
                "remoteip": remote_ip,
            },
            timeout=10,
        )
        data = response.json()
    except (httpx.HTTPError, ValueError):
        return False
    hostname = data.get("hostname")
    return (
        response.status_code == 200
        and data.get("success") is True
        and data.get("action") == TURNSTILE_ACTION
        and isinstance(hostname, str)
        and hostname in settings.turnstile_expected_hostnames
    )
