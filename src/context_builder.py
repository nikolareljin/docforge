"""Assemble repo context sections into a single string, capped at max_context_kb."""

from __future__ import annotations

from typing import Optional


class ContextBuilder:
    def __init__(self, max_context_kb: int = 128) -> None:
        self.max_bytes = max_context_kb * 1024

    def build(
        self,
        sections: dict[str, Optional[str]],
        priority_order: list[str],
        project_name: str,
        project_description: str,
    ) -> str:
        """
        Assemble extracted sections in priority order up to the byte cap.

        Returns a single markdown string ready to be sent to the LLM as user context.
        """
        header = f"# Repository: {project_name}\n\n{project_description}\n\n---\n\n"
        parts: list[str] = [header]
        used = len(header.encode("utf-8"))

        for section in priority_order:
            content = sections.get(section)
            if not content:
                continue

            section_header = f"## {section.replace('_', ' ').title()}\n\n"
            chunk = section_header + content + "\n\n"
            chunk_bytes = len(chunk.encode("utf-8"))

            if used + chunk_bytes > self.max_bytes:
                # Try to fit a truncated version.
                remaining = (
                    self.max_bytes - used - len(section_header.encode("utf-8")) - 50
                )
                if remaining > 256:
                    truncated_content = content.encode("utf-8")[:remaining].decode(
                        "utf-8", errors="replace"
                    )
                    chunk = (
                        section_header
                        + truncated_content
                        + "\n\n... [context limit reached]\n\n"
                    )
                    parts.append(chunk)
                break

            parts.append(chunk)
            used += chunk_bytes

        return "".join(parts)
