import os
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, Field

HEALTH: dict[str, bool] = {}


class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    @classmethod
    def success(cls, **data: Any) -> "ToolResult":
        return cls(ok=True, data=data)

    @classmethod
    def failure(cls, error: str) -> "ToolResult":
        return cls(ok=False, error=error)


def _env(url_key: str, secret_key: str | None = None):
    url = os.getenv(url_key)
    if not url:
        return None, None
    secret = os.getenv(secret_key, "") if secret_key else ""
    return url, secret


def _headers(secret: str | None) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if secret:
        h["Authorization"] = f"Bearer {secret}"
    return h


def _post(url: str, secret: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=20) as client:
        resp = client.post(url, json=payload, headers=_headers(secret))
        resp.raise_for_status()
        return resp.json()


class BaseTool(ABC):
    """Thin tool interface with real external API support + mock fallback."""

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        HEALTH.setdefault(self.name, True)

    def __call__(self, **kwargs: Any) -> ToolResult:
        return self.run(**kwargs)

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool action and return a ToolResult."""

    def _guard(self) -> ToolResult | None:
        if not HEALTH.get(self.name, True):
            return ToolResult.failure(f"Tool '{self.name}' is currently unavailable. Please retry later.")
        return None

    def _real_post(self, env_url_key: str, env_secret_key: str | None, payload: dict[str, Any]) -> dict[str, Any] | None:
        url, secret = _env(env_url_key, env_secret_key)
        if not url:
            return None
        try:
            return _post(url, secret, payload)
        except Exception as exc:
            return {"_fallback": True, "error": str(exc)}
