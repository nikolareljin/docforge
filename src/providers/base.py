"""Base interface for all docforge LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DocResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class DocProvider(ABC):
    @abstractmethod
    def generate(self, system: str, user: str, timeout: int = 120) -> DocResult:
        """Call the LLM and return the result."""
        ...
