"""Provider factory for docforge."""

from __future__ import annotations

import os

from .base import DocProvider, DocResult
from .anthropic import AnthropicProvider
from .openai_compat import OpenAICompatProvider


# Named provider base URLs (auto-filled when provider name is used as shortcut)
_BASE_URLS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "github": "https://models.inference.ai.azure.com",
}

# Primary env var for each provider; fallback is DOCFORGE_API_KEY
_ENV_VARS: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "together": "TOGETHER_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "github": "GITHUB_TOKEN",
}


def _resolve_api_key(provider: str) -> str:
    """Return the API key for the given provider name."""
    if provider == "ollama":
        return "ollama"  # Ollama doesn't require a real key
    if provider == "bedrock":
        return ""  # boto3 uses the AWS credential chain
    primary = _ENV_VARS.get(provider, "")
    if primary:
        key = os.environ.get(primary, "")
        if key:
            return key
    # openai_compat: try DOCFORGE_API_KEY then OPENAI_API_KEY
    fallback_order = ["DOCFORGE_API_KEY", "OPENAI_API_KEY"]
    if provider == "openai_compat":
        for var in fallback_order:
            key = os.environ.get(var, "")
            if key:
                return key
        return ""
    # All other named providers: fall back to DOCFORGE_API_KEY
    return os.environ.get("DOCFORGE_API_KEY", "")


def create_provider(ai_cfg: dict) -> DocProvider:
    """Instantiate and return the correct DocProvider from config.

    Args:
        ai_cfg: The ``ai:`` section of the docforge config dict.

    Returns:
        A DocProvider instance ready for use.

    Raises:
        ValueError: If the provider is unknown or required config is missing.
    """
    provider = ai_cfg.get("provider", "groq")
    model = ai_cfg.get("model", "llama-3.3-70b-versatile")
    max_tokens = int(ai_cfg.get("max_tokens", 8192))

    # ── Anthropic ─────────────────────────────────────────────────────────────
    if provider == "anthropic":
        api_key = _resolve_api_key("anthropic")
        if not api_key:
            raise ValueError(
                "Anthropic provider requires an API key. "
                "Set $ANTHROPIC_API_KEY or pass --api-key."
            )
        return AnthropicProvider(api_key=api_key, model=model, max_tokens=max_tokens)

    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    if provider == "bedrock":
        from .bedrock import BedrockProvider

        return BedrockProvider(
            model=model,
            max_tokens=max_tokens,
            region=ai_cfg.get("aws_region", "us-east-1"),
            profile=ai_cfg.get("aws_profile") or None,
        )

    # ── OpenAI-compatible shortcut names ─────────────────────────────────────
    if provider in _BASE_URLS:
        base_url = ai_cfg.get("base_url") or _BASE_URLS[provider]
        api_key = _resolve_api_key(provider)
        if provider != "ollama" and not api_key:
            raise ValueError(
                f"Provider {provider!r} requires an API key. "
                f"Set ${_ENV_VARS.get(provider, 'DOCFORGE_API_KEY')} or pass --api-key."
            )
        return OpenAICompatProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
        )

    # ── Generic OpenAI-compatible endpoint ────────────────────────────────────
    if provider == "openai_compat":
        base_url = ai_cfg.get("base_url", "")
        if not base_url:
            raise ValueError(
                "provider: openai_compat requires base_url in the ai: config section."
            )
        api_key = _resolve_api_key("openai_compat")
        return OpenAICompatProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
        )

    raise ValueError(
        f"Unknown provider: {provider!r}. "
        "Supported: groq, anthropic, openai_compat, together, openrouter, "
        "ollama, github, bedrock."
    )


__all__ = ["DocProvider", "DocResult", "create_provider"]
