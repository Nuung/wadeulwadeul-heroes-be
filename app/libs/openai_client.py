"""OpenAI client wrapper."""

from __future__ import annotations

import os

from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Return a singleton AsyncOpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client
