"""Optional OpenAI-compatible LLM client.

Works without a key: every call returns None and callers fall back to rules/templates.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("OLLAMA_MODEL"))


@lru_cache
def _chat_model():
    """Build a chat model if credentials exist; otherwise None."""
    if not available():
        return None
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None

    ollama = os.getenv("OLLAMA_MODEL")
    if ollama and not os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(
            model=ollama,
            base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama"),
            temperature=0,
            timeout=20,
            max_retries=0,
        )

    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0,
        timeout=20,
        max_retries=0,
    )


def complete(prompt: str, system: str | None = None, max_tokens: int = 512) -> str | None:
    """Return model text, or None if unavailable / failed."""
    model = _chat_model()
    if model is None:
        return None
    try:
        messages = []
        if system:
            messages.append(("system", system))
        messages.append(("human", prompt))
        response = model.invoke(messages, max_tokens=max_tokens)
        content = getattr(response, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
        return None
    except Exception:
        return None


def complete_json(prompt: str, system: str | None = None) -> dict[str, Any] | None:
    """Ask the model for JSON and parse it. Returns None on any failure."""
    text = complete(prompt, system=system, max_tokens=400)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
