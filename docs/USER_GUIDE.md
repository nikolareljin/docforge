# docforge — User Guide

docforge scans your repository and uses an LLM to write two documents:

- **`DEVELOPER.md`** — technical reference for contributors and developers
- **`USER_GUIDE.md`** — plain-language guide for people using your software

Both files are committed back to your repository automatically on every push
to `main`. A combined **`NOTEBOOKLM.md`** is also produced for import into
[Google NotebookLM](https://notebooklm.google.com/).

---

## Quick Start (5 minutes)

### 1. Install

From your project root:

```bash
curl -fsSL https://raw.githubusercontent.com/nikolareljin/docforge/main/install.sh | bash
```

Or manually:

```bash
git submodule add --branch main https://github.com/nikolareljin/docforge.git vendor/docforge
cp vendor/docforge/docforge.example.yml .docforge.yml
mkdir -p .github/workflows
cp vendor/docforge/templates/workflow.yml .github/workflows/docs.yml
git add .gitmodules vendor/docforge .docforge.yml .github/workflows/docs.yml
git commit -m "chore: add docforge documentation generator"
```

### 2. Configure

Edit `.docforge.yml`:

```yaml
project:
  name: "My Project"
  description: "A brief description of what this project does."
```

Everything else has sensible defaults. No API key secret needed — the default
provider uses your repository's built-in `GITHUB_TOKEN` automatically.

### 3. Push

```bash
git push
```

docforge runs on push to `main`/`master`. Docs appear in `docs/` within a
few minutes, committed by `docforge[bot]`.

---

## Configuration Reference

All settings live in `.docforge.yml` at your repository root.

### `project:`

```yaml
project:
  name: "My Project"           # Used in doc headers
  description: "..."           # Shown in the introduction
  language: "python"           # Hints the analyzer: python, go, node, php, rust…
```

### `ai:`

```yaml
ai:
  provider: "github"                   # Default — uses GITHUB_TOKEN automatically
  model: "gpt-4o"                      # Model to use
  max_tokens: 8192                     # Max response length
  # timeout_seconds: 120               # Optional request timeout override

  # Other provider examples:
  # provider: "groq"
  # model: "llama-3.3-70b-versatile"   # Free tier, fast

  # provider: "anthropic"
  # model: "claude-opus-4-6"

  # provider: "ollama"                 # Local, no API key needed
  # model: "qwen2.5:72b"

  # provider: "openai_compat"          # Any custom endpoint
  # base_url: "http://localhost:1234/v1"
  # model: "local-model"
```

### `context:`

```yaml
context:
  max_context_kb: 128      # How much of your codebase to send to the LLM
  sections:                # What to include, in priority order
    - readme
    - manifests            # package.json, pyproject.toml, go.mod, etc.
    - routes               # HTTP route definitions
    - cli                  # CLI command definitions
    - config               # .env.example, settings files
    - tests                # Sample test files
    - docker               # Dockerfile, docker-compose.yml
    - makefile
    - scripts              # Shell scripts in scripts/
    - git_log              # Last 30 commit messages
```

Remove sections you don't want included. Sections are added in order until
`max_context_kb` is reached — put the most important ones first.

### `output:`

```yaml
output:
  dir: "docs"              # Where to write the files
  generate: "both"         # "developer", "user", or "both"
  notebooklm: true         # Also write NOTEBOOKLM.md
```

### `notebooklm_upload:` (optional)

Automatically push `NOTEBOOKLM.md` to a Google NotebookLM notebook after
generation. See [NotebookLM Auto-Upload](#notebooklm-auto-upload) below.

```yaml
notebooklm_upload:
  enabled: false
  project_number: "123456789012"
  notebook_id: "your-notebook-id"
```

---

## Choosing an LLM Provider

### GitHub Models (default — no setup needed)

Uses your repository's automatic `GITHUB_TOKEN`. Works out of the box in
GitHub Actions with no secrets to configure.

```yaml
ai:
  provider: "github"
  model: "gpt-4o"
```

### Groq (free tier, very fast)

1. Sign up at [console.groq.com](https://console.groq.com) — free tier available.
2. Create an API key.
3. Add `GROQ_API_KEY` as a repository secret (Settings → Secrets → Actions).
4. Update `.docforge.yml`:

```yaml
ai:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
```

And in `.github/workflows/docs.yml`:

```yaml
      - uses: ./vendor/docforge
        with:
          api_key: ${{ secrets.GROQ_API_KEY }}
```

### Anthropic

1. Get an API key from [console.anthropic.com](https://console.anthropic.com).
2. Add `ANTHROPIC_API_KEY` as a repository secret.
3. Update `.docforge.yml`:

```yaml
ai:
  provider: "anthropic"
  model: "claude-opus-4-6"
```

### Ollama (local, no API key)

Run Ollama locally and point docforge at it:

```yaml
ai:
  provider: "ollama"
  model: "qwen2.5:72b"
  # timeout_seconds: 1800              # Optional; ollama default is already 1800s
```

No secrets needed. Run locally:

```bash
pip install httpx pyyaml
python vendor/docforge/generate.py --repo-path .
```

### Together AI, OpenRouter

```yaml
# Together AI
ai:
  provider: "together"
  model: "meta-llama/Llama-3-70b-chat-hf"
```

```yaml
# OpenRouter
ai:
  provider: "openrouter"
  model: "mistralai/mixtral-8x7b-instruct"
```

Add the corresponding secret (`TOGETHER_API_KEY` / `OPENROUTER_API_KEY`) and
pass it via `api_key:` in the workflow step.

### AWS Bedrock

```yaml
ai:
  provider: "bedrock"
  model: "anthropic.claude-3-haiku-20240307-v1:0"
  aws_region: "us-east-1"
  aws_profile: ""            # Optional — uses default credential chain if omitted
```

Requires boto3: `pip install boto3`. AWS credentials are resolved via the
standard chain (env vars, IAM role, profile).

### Any OpenAI-Compatible Endpoint

```yaml
ai:
  provider: "openai_compat"
  base_url: "http://localhost:1234/v1"
  model: "my-local-model"
```

---

## GitHub Actions Workflow

The template workflow (`.github/workflows/docs.yml`) that `install.sh` creates:

```yaml
name: "Generate Documentation"

on:
  push:
    branches: [main, master]
    paths-ignore:
      - "docs/DEVELOPER.md"
      - "docs/USER_GUIDE.md"
      - "docs/NOTEBOOKLM.md"
      - "**.md"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          submodules: recursive

      - uses: ./vendor/docforge
        with:
          config: .docforge.yml
          only: both

      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "docs: regenerate documentation [skip ci]"
          file_pattern: "docs/DEVELOPER.md docs/USER_GUIDE.md docs/NOTEBOOKLM.md"
          commit_user_name: "docforge[bot]"
          commit_user_email: "docforge[bot]@users.noreply.github.com"
```

The `paths-ignore` block prevents doc commits from re-triggering the workflow.

---

## Running Locally

```bash
pip install httpx pyyaml

# Default provider (GitHub Models) — needs GITHUB_TOKEN
GITHUB_TOKEN=ghp_... python vendor/docforge/generate.py

# Groq
GROQ_API_KEY=gsk_... python vendor/docforge/generate.py

# Anthropic
ANTHROPIC_API_KEY=sk-ant-... python vendor/docforge/generate.py

# Ollama (no key needed)
python vendor/docforge/generate.py

# With explicit options
python vendor/docforge/generate.py \
  --config .docforge.yml \
  --repo-path /path/to/repo \
  --only developer \
  --output-dir /tmp/docs
```

### CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--config PATH` | auto-detect | `.docforge.yml` location |
| `--repo-path PATH` | `.` | Repository to analyze |
| `--output-dir PATH` | from config | Override output directory |
| `--only developer\|user\|both` | from config | Which docs to generate |
| `--api-key KEY` | env var | LLM API key (sets `DOCFORGE_API_KEY`) |

---

## Output Files

| File | Audience | Contents |
|---|---|---|
| `docs/DEVELOPER.md` | Developers | Architecture, setup, API reference, testing, contributing |
| `docs/USER_GUIDE.md` | End users | Features, installation, how-tos, troubleshooting |
| `docs/NOTEBOOKLM.md` | NotebookLM | Both docs combined with source attribution footer |

---

## NotebookLM Import

### Manual import

1. Open [notebooklm.google.com](https://notebooklm.google.com/) and create a notebook.
2. Click **Add source → Upload file**.
3. Upload `docs/NOTEBOOKLM.md`.
4. NotebookLM indexes both the developer reference and user guide — you can then
   ask natural-language questions about your project.

### Auto-Upload

docforge can push `NOTEBOOKLM.md` to NotebookLM automatically after each
documentation run.

**Prerequisites:**

1. Create a GCP service account with the **Discovery Engine Editor** role.
2. Download the JSON key and add it as a repository secret named `NOTEBOOKLM_SA_KEY`.
3. Find your GCP **project number** (not project ID) in the GCP console.
4. Find your **notebook ID** in the NotebookLM URL.

**Workflow step:**

```yaml
      - uses: ./vendor/docforge
        with:
          config: .docforge.yml
          notebooklm_upload: "true"
          notebooklm_project_number: "123456789012"
          notebooklm_notebook_id: "your-notebook-id"
          notebooklm_sa_key: ${{ secrets.NOTEBOOKLM_SA_KEY }}
```

**Config file:**

```yaml
notebooklm_upload:
  enabled: true
  project_number: "123456789012"
  notebook_id: "your-notebook-id"
```

**Local use (JSON key file):**

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \
NOTEBOOKLM_PROJECT_NUMBER=123456789012 \
NOTEBOOKLM_NOTEBOOK_ID=your-notebook-id \
NOTEBOOKLM_UPLOAD=true \
python vendor/docforge/generate.py
```

---

## Custom Prompts

Copy the default prompts and edit them to change documentation style or focus:

```bash
mkdir -p prompts
cp vendor/docforge/prompts/developer.md prompts/developer.md
cp vendor/docforge/prompts/enduser.md prompts/enduser.md
```

Update `.docforge.yml`:

```yaml
prompts:
  developer: "prompts/developer.md"
  enduser: "prompts/enduser.md"
```

---

## Examples

### Minimal config (Python project)

```yaml
project:
  name: "My API"
  description: "A REST API for managing tasks."
  language: "python"
```

### Large monorepo — reduce context

```yaml
context:
  max_context_kb: 64       # Smaller budget
  sections:
    - readme
    - manifests
    - routes               # Focus on API surface
    - git_log
```

### Generate only the developer doc

```yaml
output:
  generate: "developer"
  notebooklm: false
```

Or via CLI:

```bash
python vendor/docforge/generate.py --only developer
```

### Switch to Groq mid-project

Update `.docforge.yml`:

```yaml
ai:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
```

Add secret `GROQ_API_KEY` and update the workflow step:

```yaml
      - uses: ./vendor/docforge
        with:
          api_key: ${{ secrets.GROQ_API_KEY }}
```

---

## Troubleshooting

**"Prompt file not found"**
The prompt paths in `.docforge.yml` default to `vendor/docforge/prompts/...`.
If docforge is installed somewhere else, either update the paths or let docforge
auto-resolve them by leaving the defaults and ensuring submodules are initialized:
```bash
git submodule update --init --recursive
```

**"No config file found, using defaults"**
Create `.docforge.yml` in your repository root:
```bash
cp vendor/docforge/docforge.example.yml .docforge.yml
```

**Provider error: "requires an API key"**
Set the corresponding environment variable or pass `--api-key`:
```bash
GROQ_API_KEY=gsk_... python vendor/docforge/generate.py
# or
python vendor/docforge/generate.py --api-key gsk_...
```

**NotebookLM upload: "No Google credentials found"**
Set either `NOTEBOOKLM_SA_KEY_JSON` (JSON string) or `GOOGLE_APPLICATION_CREDENTIALS`
(path to key file).

**"Context assembled: 0.0 KB"**
The analyzer found no content. Check that `--repo-path` points to the correct
directory and that the sections you listed in config actually exist in the repo.

**Docs committed but workflow re-triggers**
Ensure `paths-ignore` covers your output directory in the workflow. The default
covers `docs/*.md` and `**.md`.
