"""Slim orchestrator: loads prompts and delegates to a DocProvider."""

from __future__ import annotations

from pathlib import Path

from .providers.base import DocProvider, DocResult


def _load_prompt(prompt_path: str, action_path: str = "") -> str:
    """
    Load a prompt file. Resolves in order:
    1. Absolute path as given.
    2. Relative to current working directory.
    3. Relative to action_path (GitHub Actions $GITHUB_ACTION_PATH).
    """
    p = Path(prompt_path)
    if p.is_absolute() and p.exists():
        return p.read_text(encoding="utf-8")

    candidates = [Path(prompt_path)]
    if action_path:
        candidates.append(Path(action_path) / prompt_path)
    # Strip leading vendor/docforge/ prefix — allows running locally without submodule.
    stripped = prompt_path.replace("vendor/docforge/", "")
    candidates.append(Path(stripped))

    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    raise FileNotFoundError(
        f"Prompt file not found: {prompt_path!r}. "
        "Tried: " + ", ".join(str(c) for c in candidates)
    )


class DocGenerator:
    def __init__(self, provider: DocProvider) -> None:
        self.provider = provider

    def generate_from_prompt_file(
        self,
        prompt_path: str,
        context: str,
        action_path: str = "",
        timeout: int = 120,
    ) -> DocResult:
        system_prompt = _load_prompt(prompt_path, action_path)
        return self.provider.generate(system_prompt, context, timeout)
