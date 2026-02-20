# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Docker support** — `Dockerfile`, `docker-entrypoint.sh`, `.dockerignore` for
  containerized documentation generation. Image published to `ghcr.io/nikolareljin/docforge`.
  Volume mounts: `/repo` (source), `/output` (docs). See `docs/DOCKER.md` for full usage.
- **`.github/workflows/docker.yml`** — builds and publishes Docker image on push to main
  and on release tags. Uses GitHub Container Registry with cache layers for fast builds.
- **Multi-repo NotebookLM support** — `source_prefix` parameter in `upload_to_notebooklm()`
  prepends a prefix to the uploaded filename (e.g. `myrepo-NOTEBOOKLM.md`). Enables
  uploading docs from multiple repos to a single notebook with namespacing.
- **`notebooklm_source_prefix` action input** — exposed in `action.yml`; set to
  `${{ github.event.repository.name }}-` for automatic per-repo prefixing.
- **`requirements.txt`** — added `google-auth>=2.0` and `requests>=2.31` as core
  dependencies (NotebookLM upload now always available, not just when conditionally
  installed in Actions).
- **`docs/DOCKER.md`** — comprehensive Docker usage guide: quick start, volume mounts,
  all provider examples (GitHub, Groq, Anthropic, Ollama, Bedrock), NotebookLM upload,
  CI/CD integration (GitLab, Jenkins), troubleshooting.

### Added (from previous unreleased)
- **NotebookLM auto-upload** (`src/notebooklm.py`) — after generating `NOTEBOOKLM.md`,
  optionally upload it directly to a Google NotebookLM notebook via the Discovery
  Engine API. Enabled by setting `notebooklm_upload.enabled: true` in `.docforge.yml`
  or `NOTEBOOKLM_UPLOAD=true` in the environment.
- **`action.yml` NotebookLM inputs** — `notebooklm_upload`, `notebooklm_project_number`,
  `notebooklm_notebook_id`, `notebooklm_location`, `notebooklm_endpoint_location`,
  `notebooklm_sa_key`; Google auth deps installed only when upload is enabled.
- **`templates/workflow.yml`** — commented-out NotebookLM upload block with
  step-by-step prerequisites for consumer repositories.

## [0.1.0] — 2026-02-18

### Added

- **Multi-provider LLM architecture** (`src/providers/`) — `DocProvider` ABC and
  `DocResult` dataclass as a stable interface; `create_provider(ai_cfg)` factory
  resolves the correct provider from `.docforge.yml`.
- **GitHub Models provider** (default) — uses the OpenAI-compatible
  `https://models.inference.ai.azure.com` endpoint with `GITHUB_TOKEN`, which is
  supplied automatically in GitHub Actions workflows (zero secrets required).
- **Anthropic provider** — Messages API (`x-api-key` header, `anthropic-version`),
  with retry logic for 429 / 503 / 529 status codes.
- **OpenAI-compatible provider** — single implementation covers Groq, Together AI,
  OpenRouter, Ollama, GitHub Models, Azure OpenAI, LM Studio, and any custom
  `/chat/completions` endpoint.
- **AWS Bedrock provider** — lazy `boto3` import; supports `anthropic.*` (Messages
  format) and `meta.llama*` (prompt format) model IDs; uses the standard AWS
  credential chain (env vars, IAM role, profile).
- **`generate.py`** — CLI entry point with `--repo-path`, `--config`, `--only`,
  `--output-dir`, and `--api-key` flags; `--api-key` sets `$DOCFORGE_API_KEY` and
  is picked up by all providers as a fallback.
- **`src/analyzer.py`** — extracts repository context sections: README, manifests,
  routes, CLI definitions, config files, tests, Docker, Makefile, scripts, git log.
- **`src/context_builder.py`** — assembles sections into a budget-bounded context
  string (default 128 KB) in priority order with graceful truncation.
- **`src/generator.py`** — slim orchestrator: loads prompt files (with
  `$GITHUB_ACTION_PATH` resolution) and delegates generation to a `DocProvider`.
- **`src/writer.py`** — writes `DEVELOPER.md`, `USER_GUIDE.md`, and
  `NOTEBOOKLM.md` (combined export with source attribution footer).
- **`action.yml`** — GitHub Actions composite action; `api_key` input with
  deprecated `anthropic_api_key` alias for backward compatibility; `GITHUB_TOKEN`
  falls back to `github.token` automatically.
- **`templates/workflow.yml`** — drop-in workflow template for target repositories;
  no secrets required when using the default GitHub provider.
- **`install.sh`** — adds docforge as a git submodule (`vendor/docforge`) or a
  plain vendor copy (`--vendor`); creates `.docforge.yml` and workflow template.
- **`docforge.example.yml`** — annotated config template covering all provider
  options, context tuning, output settings, and prompt overrides.
- **`prompts/developer.md`** + **`prompts/enduser.md`** — system prompt templates
  for developer-facing and end-user-facing documentation generation.
- **`.github/workflows/ci.yml`** — CI: ruff lint + format check, import smoke test.
- **`.github/workflows/self-docs.yml`** — docforge dogfoods itself on every push
  to main; calls `generate.py` directly (bypasses the composite action) using
  `docforge.example.yml` as the config.

### Provider env-var resolution

| Provider | Primary | Fallback |
|---|---|---|
| `github` | `GITHUB_TOKEN` | `DOCFORGE_API_KEY` |
| `groq` | `GROQ_API_KEY` | `DOCFORGE_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` | — |
| `together` | `TOGETHER_API_KEY` | `DOCFORGE_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` | `DOCFORGE_API_KEY` |
| `openai_compat` | `DOCFORGE_API_KEY` | `OPENAI_API_KEY` |
| `ollama` | _(none)_ | — |
| `bedrock` | AWS credential chain | IAM role |

[0.1.0]: https://github.com/nikolareljin/docforge/releases/tag/v0.1.0
