import httpx
import pytest
from nutshellm.config import Settings
from nutshellm.security import (
    identity_key,
    new_session,
    parse_session,
    sign_session,
    verify_turnstile,
)


def test_signed_session_rejects_tampering():
    session_id, signed = new_session("secret")
    assert parse_session(signed, "secret") == session_id
    assert parse_session(signed + "x", "secret") is None
    assert parse_session(sign_session(session_id, "other"), "secret") is None


def test_quota_key_does_not_expose_ip_or_session():
    value = identity_key("ip", "203.0.113.10", "secret")
    assert len(value) == 64
    assert "203.0.113.10" not in value
    assert "session-id" not in value


@pytest.mark.asyncio
async def test_turnstile_is_bound_to_action_and_hostname():
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "action": "nutshellm_run",
                "hostname": "demo.example",
            },
        )

    settings = Settings(
        environment="production",
        turnstile_secret_key="secret",
        turnstile_expected_hostnames=("demo.example",),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await verify_turnstile("token", "203.0.113.1", settings, client)
