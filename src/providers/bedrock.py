"""AWS Bedrock provider for docforge.

Requires boto3 (optional dependency — lazy imported).
Supports Anthropic Claude models (Messages API format) and
Meta Llama models (prompt format).
"""

from __future__ import annotations

import json

from .base import DocProvider, DocResult


class BedrockProvider(DocProvider):
    def __init__(
        self,
        model: str,
        max_tokens: int,
        region: str = "us-east-1",
        profile: str | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.region = region
        self.profile = profile

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "boto3 is required for the bedrock provider. "
                "Install it with: pip install boto3"
            ) from exc

        session_kwargs: dict = {"region_name": self.region}
        if self.profile:
            session_kwargs["profile_name"] = self.profile
        session = boto3.Session(**session_kwargs)
        return session.client("bedrock-runtime")

    def generate(self, system: str, user: str, timeout: int = 120) -> DocResult:
        client = self._client()

        if self.model.startswith("anthropic."):
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                }
            )
            response = client.invoke_model(
                modelId=self.model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(response["body"].read())
            text = data["content"][0]["text"]
            usage = data.get("usage", {})
            return DocResult(
                text=text,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                model=self.model,
            )

        if self.model.startswith("meta.llama"):
            prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
            body = json.dumps(
                {
                    "prompt": prompt,
                    "max_gen_len": self.max_tokens,
                }
            )
            response = client.invoke_model(
                modelId=self.model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(response["body"].read())
            text = data.get("generation", "")
            return DocResult(
                text=text,
                input_tokens=data.get("prompt_token_count", 0),
                output_tokens=data.get("generation_token_count", 0),
                model=self.model,
            )

        raise ValueError(
            f"Unsupported Bedrock model prefix: {self.model!r}. "
            "Supported prefixes: anthropic.*, meta.llama*"
        )
