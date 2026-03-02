"""Anthropic Messages API provider for docforge."""

from __future__ import annotations

import time

import httpx

from .base import DocProvider, DocResult


_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_RETRY_STATUS_CODES = {429, 503, 529}
_RETRY_DELAY_SECONDS = 10


def _build_timeout(total_seconds: int) -> httpx.Timeout:
    """Use a short connect timeout while preserving long read timeouts."""
    total = float(total_seconds)
    connect = min(10.0, max(1.0, total))
    return httpx.Timeout(total, connect=connect)


class AnthropicProvider(DocProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def generate(self, system: str, user: str, timeout: int = 120) -> DocResult:
        timeout_cfg = _build_timeout(timeout)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = httpx.post(
                    _ANTHROPIC_MESSAGES_URL,
                    headers=headers,
                    json=payload,
                    timeout=timeout_cfg,
                )
                if response.status_code in _RETRY_STATUS_CODES and attempt == 0:
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                response.raise_for_status()
                data = response.json()
                text = data["content"][0]["text"]
                usage = data.get("usage", {})
                return DocResult(
                    text=text,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    model=data.get("model", self.model),
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if attempt == 0 and exc.response.status_code in _RETRY_STATUS_CODES:
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                raise

        raise RuntimeError(f"All retry attempts failed: {last_error}")
