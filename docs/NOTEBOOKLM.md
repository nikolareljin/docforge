# docforge — Developer Reference

docforge is a standalone documentation generator. It scans a repository,
assembles a structured context from the code, and sends it to an LLM to produce
`DEVELOPER.md`, `USER_GUIDE.md`, and `NOTEBOOKLM.md`. It is designed to be
vendored as a git submodule and triggered from GitHub Actions.

---

## Repository Layout

```
docforge/
├── generate.py                 # CLI entry point (argparse)
├── action.yml                  # GitHub Actions composite action
├── install.sh                  # Installer script (submodule or vendor copy)
├── docforge.example.yml        # Annotated config template
├── requirements.txt            # httpx, pyyaml
├── prompts/
│   ├── developer.md            # System prompt for DEVELOPER.md generation
│   └── enduser.md              # System prompt for USER_GUIDE.md generation
├── src/
│   ├── analyzer.py             # Repo scanner — extracts context sections
│   ├── context_builder.py      # Assembles sections into a byte-capped string
│   ├── generator.py            # Orchestrator — loads prompt, calls provider
│   ├── writer.py               # Writes output files
│   ├── notebooklm.py           # Google NotebookLM upload via Discovery Engine API
│   └── providers/
│       ├── __init__.py         # create_provider() factory
│       ├── base.py             # DocProvider ABC + DocResult dataclass
│       ├── anthropic.py        # Anthropic Messages API
│       ├── openai_compat.py    # OpenAI chat/completions (Groq, Together, Ollama…)
│       └── bedrock.py          # AWS Bedrock (boto3, lazy import)
├── templates/
│   └── workflow.yml            # Drop-in GitHub Actions workflow for target repos
└── .github/
    ├── workflows/ci.yml        # CI: ruff lint + import smoke test
    └── workflows/self-docs.yml # Manual self-documentation run
```

---

## Data Flow

```
generate.py (CLI)
  │
  ├── _load_config()            Load + deep-merge .docforge.yml with defaults
  ├── create_provider(ai_cfg)   Instantiate the correct DocProvider
  │
  ├── RepoAnalyzer.extract()    Scan repo → dict[section, content]
  ├── ContextBuilder.build()    Assemble sections → single markdown string (≤ N KB)
  │
  ├── DocGenerator
  │     └── generate_from_prompt_file()
  │           ├── _load_prompt()            Read system prompt file
  │           └── provider.generate()       LLM API call → DocResult
  │
  ├── DocWriter.write_developer()
  ├── DocWriter.write_user_guide()
  ├── DocWriter.write_notebooklm()
  │
  └── upload_to_notebooklm()    (optional) Push NOTEBOOKLM.md to Google NotebookLM
```

---

## Module Reference

### `src/providers/base.py`

```python
@dataclass
class DocResult:
    text: str; input_tokens: int; output_tokens: int; model: str

class DocProvider(ABC):
    @abstractmethod
    def generate(self, system: str, user: str, timeout: int = 120) -> DocResult: ...
```

### Provider env-var resolution

| Provider | Primary env var | Fallback |
|---|---|---|
| `github` | `GITHUB_TOKEN` | `DOCFORGE_API_KEY` |
| `groq` | `GROQ_API_KEY` | `DOCFORGE_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` | — |
| `together` | `TOGETHER_API_KEY` | `DOCFORGE_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` | `DOCFORGE_API_KEY` |
| `openai_compat` | `DOCFORGE_API_KEY` | `OPENAI_API_KEY` |
| `ollama` | _(none)_ | — |
| `bedrock` | AWS credential chain | IAM role |

### Context sections

| Section | What it includes |
|---|---|
| `readme` | README.md / .rst / .txt |
| `manifests` | package.json, pyproject.toml, go.mod, Cargo.toml, etc. |
| `routes` | HTTP route definitions |
| `cli` | CLI command definitions |
| `config` | .env.example, settings files |
| `tests` | Up to 5 sample test files |
| `docker` | Dockerfile, docker-compose.yml |
| `makefile` | Makefile targets |
| `scripts` | Shell scripts in scripts/ |
| `git_log` | Last 30 commit messages |

---

# docforge — User Guide

docforge scans your repository and uses an LLM to write two documents:

- **`DEVELOPER.md`** — technical reference for contributors and developers
- **`USER_GUIDE.md`** — plain-language guide for people using your software

Both files are committed back to your repository automatically on every push
to `main`. A combined **`NOTEBOOKLM.md`** is also produced for import into
[Google NotebookLM](https://notebooklm.google.com/).

---

## Quick Start

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/nikolareljin/docforge/main/install.sh | bash

# Edit project name and description
nano .docforge.yml

# Push — docs appear in docs/ within minutes
git push
```

No API key secret needed for the default GitHub provider.

---

## Provider Examples

### GitHub Models (default — no setup)
```yaml
ai:
  provider: "github"
  model: "gpt-4o"
```

### Groq (free tier)
```yaml
ai:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
```
Add secret `GROQ_API_KEY` and pass it via `api_key:` in the workflow.

### Anthropic
```yaml
ai:
  provider: "anthropic"
  model: "claude-opus-4-6"
```

### Ollama (local, no key)
```yaml
ai:
  provider: "ollama"
  model: "qwen2.5:72b"
```

### AWS Bedrock
```yaml
ai:
  provider: "bedrock"
  model: "anthropic.claude-3-haiku-20240307-v1:0"
  aws_region: "us-east-1"
```

---

## NotebookLM Auto-Upload

```yaml
notebooklm_upload:
  enabled: true
  project_number: "123456789012"
  notebook_id: "your-notebook-id"
```

Or via the action input:

```yaml
- uses: ./vendor/docforge
  with:
    notebooklm_upload: "true"
    notebooklm_project_number: "123456789012"
    notebooklm_notebook_id: "your-notebook-id"
    notebooklm_sa_key: ${{ secrets.NOTEBOOKLM_SA_KEY }}
```

Requires a GCP service account with the Discovery Engine Editor role.

---

*Generated by [docforge](https://github.com/nikolareljin/docforge) from `docforge`. Optimized for import into [Google NotebookLM](https://notebooklm.google.com/).*
