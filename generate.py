#!/usr/bin/env python3
"""docforge — Generate developer and end-user documentation from any codebase."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from src.analyzer import RepoAnalyzer
from src.context_builder import ContextBuilder
from src.generator import DocGenerator
from src.providers import create_provider
from src.writer import DocWriter


_DEFAULT_CONFIG_NAMES = (
    ".docforge.yml",
    ".docforge.yaml",
    "docforge.yml",
    "docforge.yaml",
)

_DEFAULT_CONFIG = {
    "project": {
        "name": "Project",
        "description": "",
        "language": "",
    },
    "ai": {
        "provider": "github",
        "model": "gpt-4o",
        "max_tokens": 8192,
    },
    "context": {
        "max_context_kb": 128,
        "sections": [
            "readme",
            "manifests",
            "routes",
            "cli",
            "config",
            "tests",
            "docker",
            "makefile",
            "scripts",
            "git_log",
        ],
    },
    "output": {
        "dir": "docs",
        "generate": "both",
        "notebooklm": True,
    },
    "prompts": {
        "developer": "vendor/docforge/prompts/developer.md",
        "enduser": "vendor/docforge/prompts/enduser.md",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_config(config_path: str | None, repo_path: str) -> dict:
    if config_path:
        p = Path(config_path)
        if not p.is_absolute():
            p = Path(repo_path) / p
        if not p.exists():
            print(f"error: config file not found: {p}", file=sys.stderr)
            sys.exit(1)
        with p.open(encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        return _deep_merge(_DEFAULT_CONFIG, user_config)

    for name in _DEFAULT_CONFIG_NAMES:
        p = Path(repo_path) / name
        if p.exists():
            with p.open(encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            return _deep_merge(_DEFAULT_CONFIG, user_config)

    print("warning: no config file found, using defaults", file=sys.stderr)
    return dict(_DEFAULT_CONFIG)


def _resolve_prompt_path(path: str, action_path: str) -> str:
    """Resolve a prompt path relative to the script location if not found directly."""
    if Path(path).exists():
        return path
    # When running as a submodule, prompts live next to generate.py
    script_dir = Path(__file__).parent
    local = script_dir / "prompts" / Path(path).name
    if local.exists():
        return str(local)
    if action_path:
        action_local = Path(action_path) / path
        if action_local.exists():
            return str(action_local)
    return path


def _log(msg: str) -> None:
    print(msg, flush=True)


def _resolve_timeout_seconds(ai_cfg: dict) -> int:
    """Resolve request timeout with provider-aware defaults.

    Precedence:
    1. DOCFORGE_TIMEOUT_SECONDS environment variable
    2. ai.timeout_seconds in config
    3. Provider default (ollama: 1800s, others: 120s)
    """
    env_timeout = os.environ.get("DOCFORGE_TIMEOUT_SECONDS", "").strip()
    if env_timeout:
        raw_timeout = env_timeout
    else:
        raw_timeout = ai_cfg.get("timeout_seconds")

    if raw_timeout is None:
        provider = str(ai_cfg.get("provider", "github")).strip().lower()
        return 1800 if provider == "ollama" else 120

    try:
        timeout = int(raw_timeout)
    except (TypeError, ValueError):
        print(
            "error: ai.timeout_seconds must be a positive integer "
            "(or set DOCFORGE_TIMEOUT_SECONDS).",
            file=sys.stderr,
        )
        sys.exit(1)

    if timeout <= 0:
        print(
            "error: ai.timeout_seconds must be greater than 0.",
            file=sys.stderr,
        )
        sys.exit(1)

    return timeout


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="docforge",
        description="Generate developer and end-user documentation from a codebase.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to .docforge.yml config file (default: auto-detect in repo root)",
    )
    parser.add_argument(
        "--repo-path",
        metavar="PATH",
        default=".",
        help="Path to the repository to document (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        help="Override the output directory from config",
    )
    parser.add_argument(
        "--only",
        choices=["developer", "user", "both"],
        help="Override which documents to generate (default: from config)",
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        help="API key for the configured LLM provider (sets $DOCFORGE_API_KEY)",
    )
    args = parser.parse_args()

    repo_path = str(Path(args.repo_path).resolve())
    action_path = os.environ.get("GITHUB_ACTION_PATH", "")

    # ── Load config ──────────────────────────────────────────────────────────
    config = _load_config(args.config, repo_path)

    project_cfg = config.get("project", {})
    ai_cfg = config.get("ai", {})
    ctx_cfg = config.get("context", {})
    out_cfg = config.get("output", {})
    prompts_cfg = config.get("prompts", {})

    # CLI overrides
    output_dir = args.output_dir or out_cfg.get("dir", "docs")
    generate = args.only or out_cfg.get("generate", "both")

    # ── Provider setup ────────────────────────────────────────────────────────
    if args.api_key:
        os.environ.setdefault("DOCFORGE_API_KEY", args.api_key)
    try:
        provider = create_provider(ai_cfg)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    # ── Analyze repo ──────────────────────────────────────────────────────────
    _log(f"[docforge] Analyzing repository: {repo_path}")
    analyzer = RepoAnalyzer(repo_path)
    sections_order: list[str] = ctx_cfg.get(
        "sections", _DEFAULT_CONFIG["context"]["sections"]
    )
    extracted = analyzer.extract(sections_order)
    found = [s for s, v in extracted.items() if v]
    _log(f"[docforge] Extracted sections: {', '.join(found) if found else 'none'}")

    # ── Build context ─────────────────────────────────────────────────────────
    max_ctx_kb: int = ctx_cfg.get("max_context_kb", 128)
    builder = ContextBuilder(max_context_kb=max_ctx_kb)
    context_text = builder.build(
        sections=extracted,
        priority_order=sections_order,
        project_name=project_cfg.get("name", "Project"),
        project_description=project_cfg.get("description", ""),
    )
    ctx_kb = len(context_text.encode("utf-8")) / 1024
    _log(f"[docforge] Context assembled: {ctx_kb:.1f} KB")

    # ── Generate docs ─────────────────────────────────────────────────────────
    gen = DocGenerator(provider=provider)
    writer = DocWriter(output_dir=output_dir, repo_path=repo_path)

    developer_text: str = ""
    user_guide_text: str = ""

    ai_label = f"{ai_cfg.get('provider', 'github')} / {ai_cfg.get('model', 'gpt-4o')}"
    request_timeout = _resolve_timeout_seconds(ai_cfg)
    _log(f"[docforge] Request timeout: {request_timeout}s")

    if generate in ("developer", "both"):
        prompt_path = _resolve_prompt_path(
            prompts_cfg.get("developer", "vendor/docforge/prompts/developer.md"),
            action_path,
        )
        _log(f"[docforge] Generating DEVELOPER.md ({ai_label})...")
        result = gen.generate_from_prompt_file(
            prompt_path,
            context_text,
            action_path,
            timeout=request_timeout,
        )
        developer_text = result.text
        out = writer.write_developer(developer_text)
        _log(
            f"[docforge] Written: {out}  ({result.input_tokens}→{result.output_tokens} tokens)"
        )

    if generate in ("user", "both"):
        prompt_path = _resolve_prompt_path(
            prompts_cfg.get("enduser", "vendor/docforge/prompts/enduser.md"),
            action_path,
        )
        _log(f"[docforge] Generating USER_GUIDE.md ({ai_label})...")
        result = gen.generate_from_prompt_file(
            prompt_path,
            context_text,
            action_path,
            timeout=request_timeout,
        )
        user_guide_text = result.text
        out = writer.write_user_guide(user_guide_text)
        _log(
            f"[docforge] Written: {out}  ({result.input_tokens}→{result.output_tokens} tokens)"
        )

    notebooklm_path: str = ""
    if out_cfg.get("notebooklm", True) and (developer_text or user_guide_text):
        source = str(Path(repo_path).name)
        notebooklm_path = writer.write_notebooklm(
            developer_text, user_guide_text, source
        )
        _log(f"[docforge] Written: {notebooklm_path}  (combined NotebookLM export)")

    # ── NotebookLM upload ─────────────────────────────────────────────────────
    upload_cfg = config.get("notebooklm_upload", {})
    upload_enabled = upload_cfg.get("enabled", False) or (
        os.environ.get("NOTEBOOKLM_UPLOAD", "").lower() == "true"
    )
    if upload_enabled and notebooklm_path:
        project_number = upload_cfg.get("project_number") or os.environ.get(
            "NOTEBOOKLM_PROJECT_NUMBER", ""
        )
        notebook_id = upload_cfg.get("notebook_id") or os.environ.get(
            "NOTEBOOKLM_NOTEBOOK_ID", ""
        )
        location = upload_cfg.get("location") or os.environ.get(
            "NOTEBOOKLM_LOCATION", "global"
        )
        endpoint_location = upload_cfg.get("endpoint_location") or os.environ.get(
            "NOTEBOOKLM_ENDPOINT_LOCATION", "global"
        )
        source_prefix = upload_cfg.get("source_prefix", "") or os.environ.get(
            "NOTEBOOKLM_SOURCE_PREFIX", ""
        )
        _log(f"[docforge] Uploading {Path(notebooklm_path).name} to NotebookLM...")
        try:
            from src.notebooklm import upload_to_notebooklm

            result = upload_to_notebooklm(
                file_path=notebooklm_path,
                project_number=project_number,
                notebook_id=notebook_id,
                location=location,
                endpoint_location=endpoint_location,
                source_prefix=source_prefix,
            )
            _log(f"[docforge] NotebookLM upload complete: {result}")
        except (ImportError, ValueError) as exc:
            print(f"error: NotebookLM upload failed: {exc}", file=sys.stderr)
            sys.exit(1)

    _log("[docforge] Done.")


if __name__ == "__main__":
    main()
