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

Defines the interface every provider must implement.

```python
@dataclass
class DocResult:
    text: str           # Generated markdown text
    input_tokens: int   # Tokens consumed by the prompt
    output_tokens: int  # Tokens in the response
    model: str          # Model ID actually used

class DocProvider(ABC):
    @abstractmethod
    def generate(self, system: str, user: str, timeout: int = 120) -> DocResult: ...
```

### `src/providers/__init__.py` — `create_provider(ai_cfg)`

Factory function. Reads the `ai:` config dict and returns the correct provider.

```python
from src.providers import create_provider

provider = create_provider({
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "max_tokens": 8192,
})
```

**Named shortcut providers** (auto-fill `base_url`):

| Name | Base URL | Primary env var |
|---|---|---|
| `github` | `https://models.inference.ai.azure.com` | `GITHUB_TOKEN` |
| `groq` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` |
| `together` | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| `ollama` | `http://localhost:11434/v1` | _(none required)_ |

**Special providers**: `anthropic`, `bedrock`, `openai_compat`.

`openai_compat` requires `base_url` to be set explicitly in config:

```yaml
ai:
  provider: openai_compat
  base_url: "http://localhost:1234/v1"
  model: "local-model"
```

**API key resolution order** (for all named providers with a fallback):

1. Provider-specific env var (e.g. `GROQ_API_KEY`)
2. `DOCFORGE_API_KEY`
3. `--api-key` flag → sets `DOCFORGE_API_KEY` via `os.environ.setdefault`

### `src/analyzer.py` — `RepoAnalyzer`

Scans the repository root and extracts sections.

```python
analyzer = RepoAnalyzer("/path/to/repo")
sections = analyzer.extract(["readme", "manifests", "routes", "git_log"])
# → {"readme": "## README.md\n\n...", "manifests": "### package.json\n...", ...}
```

**Extracted sections:**

| Section | Strategy |
|---|---|
| `readme` | Reads `README.md`, `.rst`, `.txt` — first match wins |
| `manifests` | Reads known manifest filenames from repo root |
| `routes` | Pattern-searches `*.py/.ts/.go/.rb/.php/.rs` for route decorators |
| `cli` | Pattern-searches for CLI framework patterns (Click, Cobra, argparse…) |
| `config` | Reads `.env.example`, `config.yml`, `settings.py`, etc. |
| `tests` | Up to 5 files from `tests/`, `test/`, `spec/`, `__tests__/` |
| `docker` | Reads `Dockerfile`, `docker-compose.yml` |
| `makefile` | Reads `Makefile` |
| `scripts` | Up to 6 `.sh`/`.bash` files from `scripts/` |
| `git_log` | Last 30 commits via `git log --oneline -30` |

**Skipped directories**: `.git`, `node_modules`, `__pycache__`, `.venv`, `vendor`,
`dist`, `build`, `target`, `bin`, `obj`, `.next`, `.nuxt`.

**File read limit**: 32 KB per file. Larger files are truncated with a `[truncated]` marker.

### `src/context_builder.py` — `ContextBuilder`

Assembles extracted sections into a single markdown string that fits within a byte budget.

```python
builder = ContextBuilder(max_context_kb=128)
context = builder.build(
    sections=extracted,
    priority_order=["readme", "manifests", "routes"],
    project_name="My Project",
    project_description="Short description.",
)
```

Sections are added in `priority_order` until `max_context_kb` is reached.
If the next section would overflow the budget, it is partially included with
a `[context limit reached]` trailer. Remaining sections are dropped.

### `src/generator.py` — `DocGenerator`

Thin orchestrator that resolves prompt files and calls the provider.

```python
from src.generator import DocGenerator

gen = DocGenerator(provider=provider)
result = gen.generate_from_prompt_file(
    prompt_path="prompts/developer.md",
    context=context_text,
    action_path=os.environ.get("GITHUB_ACTION_PATH", ""),
    timeout=120,
)
print(result.text)            # generated markdown
print(result.input_tokens)    # token usage
```

**Prompt file resolution order:**
1. Absolute path as given
2. Relative to current working directory
3. Relative to `$GITHUB_ACTION_PATH` (composite action context)
4. Path with `vendor/docforge/` prefix stripped (local dev without submodule)

### `src/writer.py` — `DocWriter`

```python
writer = DocWriter(output_dir="docs", repo_path="/path/to/repo")
writer.write_developer(developer_text)    # → docs/DEVELOPER.md
writer.write_user_guide(user_guide_text)  # → docs/USER_GUIDE.md
writer.write_notebooklm(developer_text, user_guide_text, source="myrepo")
# → docs/NOTEBOOKLM.md  (combined, with attribution footer)
```

### `src/notebooklm.py` — `upload_to_notebooklm()`

Uploads a markdown file to a Google NotebookLM notebook via the Discovery Engine API.

```python
from src.notebooklm import upload_to_notebooklm

result = upload_to_notebooklm(
    file_path="docs/NOTEBOOKLM.md",
    project_number="123456789012",
    notebook_id="your-notebook-id",
    location="global",               # default
    endpoint_location="global",      # default
)
```

**Credential resolution order:**

1. `sa_key_json` argument (JSON string)
2. `sa_key_path` argument (file path)
3. `NOTEBOOKLM_SA_KEY_JSON` env var (JSON string — recommended for CI)
4. `GOOGLE_APPLICATION_CREDENTIALS` env var (file path)

Requires `google-auth` and `requests`: `pip install google-auth requests`

---

## Configuration System

`generate.py` merges `_DEFAULT_CONFIG` (hardcoded) with the user's `.docforge.yml`
using a recursive deep-merge (`_deep_merge`). The user file is always loaded from
the repository being documented, not from docforge's own directory.

**Config search order** (when `--config` is not passed):
1. `.docforge.yml`
2. `.docforge.yaml`
3. `docforge.yml`
4. `docforge.yaml`

If none found, defaults are used with a warning.

**Default config (as of v0.1.0):**
```python
{
    "ai": {
        "provider": "github",
        "model": "gpt-4o",
        "max_tokens": 8192,
    },
    "context": {
        "max_context_kb": 128,
        "sections": ["readme", "manifests", "routes", "cli",
                     "config", "tests", "docker", "makefile", "scripts", "git_log"],
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
```

---

## Adding a New Provider

1. Create `src/providers/myprovider.py` implementing `DocProvider`.
2. Add the `base_url` to `_BASE_URLS` in `src/providers/__init__.py` (if OpenAI-compatible).
3. Add the primary env var to `_ENV_VARS`.
4. If it requires custom logic (non-OpenAI wire format), add a branch in `create_provider()`.

Example — adding a hypothetical `mistral` provider:

```python
# src/providers/__init__.py

_BASE_URLS["mistral"] = "https://api.mistral.ai/v1"
_ENV_VARS["mistral"] = "MISTRAL_API_KEY"
# No further changes needed — it uses the OpenAI-compatible wire format.
```

---

## GitHub Actions Integration

### Composite Action (`action.yml`)

```yaml
- uses: ./vendor/docforge
  with:
    api_key: ${{ secrets.GROQ_API_KEY }}   # optional for github provider
    config: .docforge.yml
    only: both
    # NotebookLM upload (optional):
    notebooklm_upload: "true"
    notebooklm_project_number: "123456789012"
    notebooklm_notebook_id: "your-notebook-id"
    notebooklm_sa_key: ${{ secrets.NOTEBOOKLM_SA_KEY }}
```

**Inputs:**

| Input | Default | Description |
|---|---|---|
| `api_key` | `""` | LLM provider API key → sets `DOCFORGE_API_KEY` |
| `anthropic_api_key` | `""` | Deprecated alias for `api_key` |
| `config` | `.docforge.yml` | Config file path relative to repo root |
| `repo_path` | `.` | Repository to document |
| `only` | `both` | `developer` \| `user` \| `both` |
| `output_dir` | `""` | Override output directory |
| `notebooklm_upload` | `false` | Enable NotebookLM upload |
| `notebooklm_project_number` | `""` | GCP project number |
| `notebooklm_notebook_id` | `""` | NotebookLM notebook ID |
| `notebooklm_location` | `global` | GCP resource location |
| `notebooklm_endpoint_location` | `global` | Discovery Engine endpoint location |
| `notebooklm_sa_key` | `""` | Service account JSON string |

**Environment variables set by the action:**

| Variable | Value |
|---|---|
| `DOCFORGE_API_KEY` | `api_key` input |
| `GROQ_API_KEY` | `api_key` input |
| `ANTHROPIC_API_KEY` | `api_key` input |
| `GITHUB_TOKEN` | `api_key` input or `github.token` (automatic fallback) |
| `NOTEBOOKLM_UPLOAD` | `notebooklm_upload` input |
| `NOTEBOOKLM_PROJECT_NUMBER` | `notebooklm_project_number` input |
| `NOTEBOOKLM_NOTEBOOK_ID` | `notebooklm_notebook_id` input |
| `NOTEBOOKLM_SA_KEY_JSON` | `notebooklm_sa_key` input |

### Preventing CI Loops

The template workflow uses `paths-ignore` to avoid re-triggering on doc commits:

```yaml
on:
  push:
    paths-ignore:
      - "docs/DEVELOPER.md"
      - "docs/USER_GUIDE.md"
      - "docs/NOTEBOOKLM.md"
      - "**.md"
```

The auto-commit step also appends `[skip ci]` to the commit message as a secondary guard.

---

## Development

### Requirements

```bash
pip install httpx>=0.27 pyyaml>=6.0
# Optional: for linting
pip install ruff
# Optional: for NotebookLM upload
pip install google-auth requests
```

### Linting

```bash
ruff check generate.py src/
ruff format --check generate.py src/
```

### Smoke Test

```bash
python3 -c "
from src.providers import create_provider
import os
os.environ['GITHUB_TOKEN'] = 'test'
p = create_provider({'provider': 'github', 'model': 'gpt-4o', 'max_tokens': 8192})
print(type(p).__name__, p.base_url)
"
```

### CI

`.github/workflows/ci.yml` runs on every push: ruff lint, ruff format check,
and the provider smoke test above.

### Self-Documentation

`.github/workflows/self-docs.yml` is `workflow_dispatch` only — trigger manually
from the Actions tab to regenerate `docs/` for docforge itself. It uses
`docforge.example.yml` as the config and `GITHUB_TOKEN` (auto-provided) as the
LLM API key via the GitHub Models provider.
