# docforge — Docker Usage

docforge is available as a Docker image for running documentation generation
without installing Python or dependencies locally.

---

## Quick Start

```bash
# Pull the image
docker pull ghcr.io/nikolareljin/docforge:latest

# Run on your current directory
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  ghcr.io/nikolareljin/docforge:latest
```

Docs appear in `./docs/`.

This quick start uses the default provider (`github`), so `GITHUB_TOKEN` must
be set in your environment.

---

## Image Tags

| Tag | Description |
|---|---|
| `latest` | Latest commit on `main` branch |
| `v1` | Latest stable v1.x.x release |
| `v0.1.0` | Specific version |

---

## Volume Mounts

The image expects two volumes:

| Mount | Purpose | Mode |
|---|---|---|
| `/repo` | Repository to document | `ro` (read-only) recommended |
| `/output` | Where docs are written | `rw` (read-write) |

**Example:**

```bash
docker run --rm \
  -v "/path/to/myproject:/repo:ro" \
  -v "/path/to/myproject/docs:/output" \
  ghcr.io/nikolareljin/docforge:latest
```

---

## Configuration

### Option 1: Config file in the repository (recommended; required for non-default behavior)

Place `.docforge.yml` in your repository root:

```yaml
project:
  name: "My Project"
  description: "A brief description."

ai:
  provider: "github"
  model: "gpt-4o"
```

Mount the repo and run:

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  ghcr.io/nikolareljin/docforge:latest
```

The image auto-detects `.docforge.yml` at `/repo/.docforge.yml`.

### Option 2: External config file

Store the config elsewhere and mount it explicitly:

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -v "/path/to/my-config.yml:/config/docforge.yml:ro" \
  -e CONFIG_FILE=/config/docforge.yml \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  ghcr.io/nikolareljin/docforge:latest
```

### Option 3: Default config (no `.docforge.yml`)

If no `.docforge.yml` exists, the image uses the built-in default config
(`docforge.example.yml`):

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  ghcr.io/nikolareljin/docforge:latest
```

Defaults in this mode:
- Provider: `github`
- Model: `gpt-4o`
- Requirement: `GITHUB_TOKEN` must be set

### When `.docforge.yml` is required

You must provide a config file (in-repo or external via `CONFIG_FILE`) when you
want anything non-default, for example:
- `ai.provider: ollama`, `groq`, `anthropic`, `openrouter`, `together`, `bedrock`, or custom `openai_compat`
- Non-default model selection
- Custom `timeout_seconds`, context/output settings, or prompt paths

---

## Environment Variables

### Required (provider-dependent)

| Variable | Provider | Notes |
|---|---|---|
| `GITHUB_TOKEN` | `github` | **Default provider.** Use your GitHub PAT. |
| `GROQ_API_KEY` | `groq` | Free tier available at console.groq.com |
| `ANTHROPIC_API_KEY` | `anthropic` | Claude models |
| `TOGETHER_API_KEY` | `together` | Open-source models |
| `OPENROUTER_API_KEY` | `openrouter` | Multi-provider routing |
| `DOCFORGE_API_KEY` | `openai_compat` | Generic fallback for custom endpoints |

For `ollama` (local) or `bedrock` (AWS), no key is needed.

### Optional (override config file)

| Variable | Default | Description |
|---|---|---|
| `CONFIG_FILE` | `/repo/.docforge.yml` | Path to config file |
| `REPO_PATH` | `/repo` | Repository root inside container |
| `OUTPUT_DIR` | `/output` | Where to write docs inside container |
| `DOCFORGE_TIMEOUT_SECONDS` | provider-dependent | Override LLM request timeout (default: `1800` for `ollama`, otherwise `120`) |

---

## Provider Examples

### GitHub Models (default)

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  ghcr.io/nikolareljin/docforge:latest
```

Get a GitHub PAT from [github.com/settings/tokens](https://github.com/settings/tokens) (fine-grained, no special scopes needed).

### Groq

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GROQ_API_KEY="${GROQ_API_KEY}" \
  ghcr.io/nikolareljin/docforge:latest
```

Config file:

```yaml
ai:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
```

### Anthropic

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  ghcr.io/nikolareljin/docforge:latest
```

Config file:

```yaml
ai:
  provider: "anthropic"
  model: "claude-opus-4-6"
```

### Ollama (local)

Run Ollama on your host, then connect the container to the host network:

```bash
docker run --rm \
  --network host \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  ghcr.io/nikolareljin/docforge:latest
```

This requires `.docforge.yml` (or an external `CONFIG_FILE`) with
`ai.provider: "ollama"`.

Config file:

```yaml
ai:
  provider: "ollama"
  model: "qwen2.5:72b"
  # Optional override. If omitted, ollama defaults to 1800s timeout.
  timeout_seconds: 1800
```

Ollama must be listening on `http://localhost:11434`.

For very slow local models, you can also set a runtime override:

```bash
docker run --rm \
  --network host \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e DOCFORGE_TIMEOUT_SECONDS=3600 \
  ghcr.io/nikolareljin/docforge:latest
```

### AWS Bedrock

Pass AWS credentials as environment variables:

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  -e AWS_REGION="us-east-1" \
  ghcr.io/nikolareljin/docforge:latest
```

Config file:

```yaml
ai:
  provider: "bedrock"
  model: "anthropic.claude-3-haiku-20240307-v1:0"
  aws_region: "us-east-1"
```

---

## CLI Overrides

Pass any `generate.py` flags after the image name to override defaults:

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  ghcr.io/nikolareljin/docforge:latest \
  --only developer \
  --config /repo/custom-config.yml
```

Available flags: `--config`, `--repo-path`, `--output-dir`, `--only`, `--api-key`.

---

## NotebookLM Upload

To enable auto-upload from Docker, mount the service account key and set env vars:

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -v "/path/to/sa-key.json:/sa-key.json:ro" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e NOTEBOOKLM_UPLOAD=true \
  -e NOTEBOOKLM_PROJECT_NUMBER="123456789012" \
  -e NOTEBOOKLM_NOTEBOOK_ID="your-notebook-id" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/sa-key.json \
  ghcr.io/nikolareljin/docforge:latest
```

Or pass the key as a JSON string (recommended for CI):

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e NOTEBOOKLM_UPLOAD=true \
  -e NOTEBOOKLM_PROJECT_NUMBER="123456789012" \
  -e NOTEBOOKLM_NOTEBOOK_ID="your-notebook-id" \
  -e NOTEBOOKLM_SA_KEY_JSON="${SA_KEY_JSON}" \
  ghcr.io/nikolareljin/docforge:latest
```

The image includes `google-auth` and `requests` for NotebookLM upload.

---

## Building the Image Locally

```bash
cd /path/to/docforge
docker build -t docforge:local .
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  docforge:local
```

---

## CI/CD Integration

### GitHub Actions

Use the official composite action instead of Docker for better integration.
See [`.github/workflows/docs.yml`](../.github/workflows/docs.yml) in the template.

### GitLab CI

```yaml
generate-docs:
  image: ghcr.io/nikolareljin/docforge:latest
  variables:
    GITHUB_TOKEN: $GITHUB_TOKEN
  script:
    - python /app/generate.py --repo-path . --output-dir docs
  artifacts:
    paths:
      - docs/
```

### Jenkins

```groovy
docker.image('ghcr.io/nikolareljin/docforge:latest').inside('-v $WORKSPACE:/repo:ro -v $WORKSPACE/docs:/output') {
    withEnv(["GITHUB_TOKEN=${env.GITHUB_TOKEN}"]) {
        sh '/app/docker-entrypoint.sh'
    }
}
```

---

## Troubleshooting

**"Permission denied" when writing to `/output`**

The container runs as root by default. Ensure the output directory is writable:

```bash
chmod 777 docs/  # or use your user's UID
docker run --rm --user $(id -u):$(id -g) \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  ghcr.io/nikolareljin/docforge:latest
```

**"No config file found, using defaults"**

If you see this warning and expected a config file, check:

1. `.docforge.yml` exists in the repository root
2. The repo volume is mounted at `/repo`
3. The file is readable (`chmod 644 .docforge.yml`)

**"Provider 'github' requires an API key"**

Pass `GITHUB_TOKEN` as an environment variable:

```bash
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="ghp_your_token_here" \
  ghcr.io/nikolareljin/docforge:latest
```

**Ollama connection refused**

Use `--network host` (Linux) or `host.docker.internal` (macOS/Windows):

```yaml
# .docforge.yml on macOS/Windows
ai:
  provider: "ollama"
  model: "qwen2.5:72b"
  base_url: "http://host.docker.internal:11434/v1"
```

---

## Image Size

The image is based on `python:3.11-slim` and includes:

- Python 3.11
- `httpx`, `pyyaml` (core dependencies)
- `google-auth`, `requests` (NotebookLM upload)
- `git` (for `git_log` section analysis)

Approximate size: **150 MB** compressed.

---

## Security Notes

- The repository is mounted **read-only** (`ro`) to prevent accidental modifications.
- The output directory is **read-write** (`rw`) — only docs are written.
- API keys are passed as environment variables — never baked into the image.
- The image runs as `root` by default. Use `--user` for least privilege in production.
