# docforge

Auto-generate developer and end-user documentation from any codebase. Triggered by GitHub Actions on push to main/master. Output is optimized for [Google NotebookLM](https://notebooklm.google.com/) import.

Designed to be vendored as a git submodule into any repository in your ecosystem.

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

This adds docforge as a git submodule at `vendor/docforge`, creates `.docforge.yml`, and adds the GitHub Actions workflow.

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

Edit `.docforge.yml` in your repo root. All fields are optional — sensible defaults are used for anything omitted.

```yaml
project:
  name: "My Project"
  description: "A brief description of what this project does."
  language: "python"   # python, go, node, php, rust, ruby, ...

ai:
  model: "claude-opus-4-6"
  max_tokens: 8192

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

prompts:
  developer: "vendor/docforge/prompts/developer.md"
  enduser: "vendor/docforge/prompts/enduser.md"
```

See [`docforge.example.yml`](docforge.example.yml) for the fully-commented version.

---

## GitHub Actions Setup

1. Add `ANTHROPIC_API_KEY` as a repository secret (Settings → Secrets → Actions).
2. The workflow at `.github/workflows/docs.yml` runs on every push to `main`/`master`.
3. Generated docs are committed back to the repository automatically.

The workflow uses `paths-ignore` on the generated doc files to prevent infinite loops.

---

## Manual Run

```bash
pip install httpx pyyaml

# Run from your project root (with docforge as a submodule):
ANTHROPIC_API_KEY=sk-ant-... python vendor/docforge/generate.py

# Or from any directory with explicit paths:
ANTHROPIC_API_KEY=sk-ant-... python /path/to/docforge/generate.py \
  --config /path/to/repo/.docforge.yml \
  --repo-path /path/to/repo \
  --output-dir /tmp/docs
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--config PATH` | auto-detect | Path to `.docforge.yml` |
| `--repo-path PATH` | `.` | Repository to analyze |
| `--output-dir PATH` | from config | Override output directory |
| `--only developer\|user\|both` | from config | Which docs to generate |
| `--api-key KEY` | `$ANTHROPIC_API_KEY` | API key |

---

## Output Files

All files are written to the `docs/` directory (or `output.dir` in config):

| File | Description |
|------|-------------|
| `docs/DEVELOPER.md` | Technical reference for developers: setup, architecture, API, testing |
| `docs/USER_GUIDE.md` | Plain-language guide for end users: features, how-tos, troubleshooting |
| `docs/NOTEBOOKLM.md` | Combined file with source footer, optimized for NotebookLM import |

---

## NotebookLM Export

1. After generation, open [notebooklm.google.com](https://notebooklm.google.com/)
2. Create a new notebook
3. Click **Add source** → **Upload file**
4. Upload `docs/NOTEBOOKLM.md`
5. NotebookLM will index both the developer reference and user guide, enabling natural-language Q&A over your documentation

---

## Custom Prompts

To customize the documentation style, copy the prompts and edit them:

```bash
cp vendor/docforge/prompts/developer.md prompts/developer.md
cp vendor/docforge/prompts/enduser.md prompts/enduser.md
```

Then update `.docforge.yml`:

```yaml
prompts:
  developer: "prompts/developer.md"
  enduser: "prompts/enduser.md"
```

---

## Context Sections

docforge analyzes your repository and assembles context in priority order:

| Section | What it includes |
|---------|-----------------|
| `readme` | README.md / README.rst / README.txt |
| `manifests` | package.json, pyproject.toml, go.mod, Cargo.toml, etc. |
| `routes` | HTTP route definitions (FastAPI, Flask, Express, Gin, etc.) |
| `cli` | CLI command definitions (Click, Cobra, argparse, etc.) |
| `config` | .env.example, config files, settings modules |
| `tests` | Sample test files |
| `docker` | Dockerfile, docker-compose.yml |
| `makefile` | Makefile targets |
| `scripts` | Shell scripts in scripts/ |
| `git_log` | Last 30 commit messages |

Sections are included in order until `max_context_kb` is reached.

---

## Requirements

- Python 3.9+
- `httpx>=0.27`
- `pyyaml>=6.0`
- An API key (`ANTHROPIC_API_KEY`)

---

## License

MIT
