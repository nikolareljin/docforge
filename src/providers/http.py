"""Shared HTTP utilities for provider integrations."""

from __future__ import annotations

import httpx


def build_timeout(total_seconds: int) -> httpx.Timeout:
    """Use a short connect timeout while preserving long read timeouts."""
    total = float(total_seconds)
    connect = min(10.0, max(1.0, total))
    return httpx.Timeout(timeout=total, connect=connect)
