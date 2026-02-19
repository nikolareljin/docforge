"""OpenAI-compatible chat/completions provider for docforge.

Supports Groq, Together AI, OpenRouter, Ollama, GitHub Copilot, Azure OpenAI,
LM Studio, and any endpoint that speaks the OpenAI chat completions wire format.
"""

from __future__ import annotations

import time

import httpx

from .base import DocProvider, DocResult


_RETRY_STATUS_CODES = {429, 503, 529}
_RETRY_DELAY_SECONDS = 10


class OpenAICompatProvider(DocProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def generate(self, system: str, user: str, timeout: int = 120) -> DocResult:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = httpx.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                )
                if response.status_code in _RETRY_STATUS_CODES and attempt == 0:
                    time.sleep(_RETRY_DELAY_SECONDS)
                    continue
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return DocResult(
                    text=text,
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
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
