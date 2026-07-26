"""ASGI and CLI entry points."""

from __future__ import annotations

from .api import create_app

app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("nutshellm.main:app", host="0.0.0.0", port=8000)
