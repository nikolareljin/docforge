# docforge

[![Website](https://img.shields.io/badge/docs-GitHub%20Pages-F5C451)](https://nikolareljin.github.io/docforge/)

Auto-generate developer and end-user documentation from any codebase.
Triggered by GitHub Actions on push to main/master. Output is optimized for
[Google NotebookLM](https://notebooklm.google.com/) import.

Designed to be vendored as a git submodule into any repository in your ecosystem.
No API key secrets needed — the default provider uses `GITHUB_TOKEN` automatically.

Project overview and quick start: <https://nikolareljin.github.io/docforge/>.

---

## Quick Install

```bash
# From your project root:
curl -fsSL https://raw.githubusercontent.com/nikolareljin/docforge/main/install.sh | bash
```

Or if docforge is already cloned locally:

```bash
/path/to/docforge/install.sh --target /path/to/your-repo
```

This adds docforge as a git submodule at `vendor/docforge`, creates `.docforge.yml`,
and adds the GitHub Actions workflow.

---

## Manual Install

```bash
# Add as a git submodule
git submodule add --branch main https://github.com/nikolareljin/docforge.git vendor/docforge

# Copy and customize config
cp vendor/docforge/docforge.example.yml .docforge.yml

# Add the workflow
mkdir -p .github/workflows
cp vendor/docforge/templates/workflow.yml .github/workflows/docs.yml

# Commit
git add .gitmodules vendor/docforge .docforge.yml .github/workflows/docs.yml
git commit -m "chore: add docforge documentation generator"
```

---

## Configuration

Edit `.docforge.yml` in your repo root. All fields are optional.

```yaml
project:
  name: "My Project"
  description: "A brief description of what this project does."
  language: "python"   # python, go, node, php, rust, ruby, ...

ai:
  provider: "github"   # default — uses GITHUB_TOKEN automatically
  model: "gpt-4o"
  max_tokens: 8192
  # timeout_seconds: 120  # optional; default is 1800 for ollama, 120 otherwise
  # NOTE: DOCFORGE_TIMEOUT_SECONDS env var overrides ai.timeout_seconds at runtime.

context:
  max_context_kb: 128
  sections:
    - readme
    - manifests
    - routes
    - cli
    - config
    - tests
    - docker
    - makefile
    - scripts
    - git_log

output:
  dir: "docs"          # output directory (relative to repo root)
  generate: "both"     # developer | user | both
  notebooklm: true     # also write NOTEBOOKLM.md
```

See [`docforge.example.yml`](docforge.example.yml) for the fully-commented version.

When running `generate.py` locally without `--config`, if `.docforge.yml` is
missing, docforge falls back to built-in defaults (`provider: github`,
`model: gpt-4o`) and requires `GITHUB_TOKEN`.
The GitHub Action defaults to `config: .docforge.yml`, so it will fail if that
file is missing unless you override the action `config` input.
To run with any non-default provider (for example `ollama`), create
`.docforge.yml` (or pass an explicit config path).

---

## Supported LLM Providers

| Provider | Key | Notes |
|---|---|---|
| `github` | `GITHUB_TOKEN` (auto) | **Default.** Free, no setup. |
| `groq` | `GROQ_API_KEY` | Free tier, fast. |
| `anthropic` | `ANTHROPIC_API_KEY` | Claude models. |
| `together` | `TOGETHER_API_KEY` | Open-source models. |
| `openrouter` | `OPENROUTER_API_KEY` | Multi-provider routing. |
| `ollama` | _(none)_ | Local inference. |
| `openai_compat` | `DOCFORGE_API_KEY` | Any `/chat/completions` endpoint. |
| `bedrock` | AWS credentials | Anthropic + Llama on AWS. |

---

## GitHub Actions Setup

1. The workflow at `.github/workflows/docs.yml` runs on every push to `main`/`master`.
2. No secrets are required for the default GitHub provider — `GITHUB_TOKEN` is
   provided automatically by the Actions runner.
3. To use a different provider, add its API key as a repository secret and pass
   it via `api_key:` in the workflow step.
4. Generated docs are committed back to the repository automatically.

The workflow uses `paths-ignore` on the generated doc files to prevent infinite loops.

---

## Manual Run

```bash
pip install httpx pyyaml

# Default provider (GitHub Models)
GITHUB_TOKEN=ghp_... python vendor/docforge/generate.py

# Groq
GROQ_API_KEY=gsk_... python vendor/docforge/generate.py

# Ollama (no key needed)
python vendor/docforge/generate.py

# Explicit options
python vendor/docforge/generate.py \
  --config .docforge.yml \
  --repo-path /path/to/repo \
  --only developer
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--config PATH` | auto-detect | Path to `.docforge.yml` |
| `--repo-path PATH` | `.` | Repository to analyze |
| `--output-dir PATH` | from config | Override output directory |
| `--only developer\|user\|both` | from config | Which docs to generate |
| `--api-key KEY` | env var | API key (sets `DOCFORGE_API_KEY`) |

---

## Output Files

| File | Description |
|------|-------------|
| `docs/DEVELOPER.md` | Technical reference: setup, architecture, API, testing |
| `docs/USER_GUIDE.md` | Plain-language guide: features, how-tos, troubleshooting |
| `docs/NOTEBOOKLM.md` | Combined file with source footer, optimized for NotebookLM import |

---

## NotebookLM

### Manual import

1. Open [notebooklm.google.com](https://notebooklm.google.com/) and create a notebook.
2. Click **Add source → Upload file**.
3. Upload `docs/NOTEBOOKLM.md`.

### Auto-upload

docforge can push `NOTEBOOKLM.md` directly to NotebookLM after generation.
See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md#notebooklm-auto-upload) for setup.

---

## Documentation

- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — installation, configuration, provider examples, troubleshooting
- [`docs/DEVELOPER.md`](docs/DEVELOPER.md) — architecture, module reference, contributing

---

## Requirements

- Python 3.9+
- `httpx>=0.27`
- `pyyaml>=6.0`
- An LLM provider (default: GitHub Models via `GITHUB_TOKEN`)

---

## License

MIT

---

## Clone traffic

![Clone traffic](https://raw.githubusercontent.com/nikolareljin/stats/main/charts/docforge.svg)

_Updated daily. Total and unique cloners over the last 14 days._
