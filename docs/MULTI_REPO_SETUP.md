# Multi-Repository Documentation with docforge

This guide shows how to set up docforge across multiple repositories with
automated NotebookLM uploads to a **single shared notebook**.

---

## Architecture

```
Repo A (myapi)         ────┐
Repo B (myfrontend)    ────┼──→  Single NotebookLM Notebook
Repo C (mylib)         ────┘     (namespaced by repo name)
```

Each repository:
1. Generates its own `NOTEBOOKLM.md` on push to `main`.
2. Uploads to the **same** NotebookLM notebook with a unique prefix.
3. Files in the notebook: `myapi-NOTEBOOKLM.md`, `myfrontend-NOTEBOOKLM.md`, `mylib-NOTEBOOKLM.md`.

---

## Prerequisites

### 1. Create a Google Cloud Project + NotebookLM Notebook

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project.
2. Note the **project number** (not project ID) from the dashboard.
3. Go to [notebooklm.google.com](https://notebooklm.google.com) and create a notebook.
4. Extract the **notebook ID** from the URL: `https://notebooklm.google.com/notebook/abc123...` → `abc123...`

### 2. Create a Service Account

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Create service account
gcloud iam service-accounts create docforge-uploader \
  --display-name="docforge NotebookLM uploader" \
  --project="${PROJECT_ID}"

# Grant Discovery Engine Editor role
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:docforge-uploader@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/discoveryengine.editor"

# Download JSON key
gcloud iam service-accounts keys create sa-key.json \
  --iam-account="docforge-uploader@${PROJECT_ID}.iam.gserviceaccount.com"
```

**Store the entire contents of `sa-key.json` as a GitHub organization secret**
named `NOTEBOOKLM_SA_KEY`. This allows all repos in the organization to reuse it.

---

## Per-Repository Setup

### Step 1: Install docforge

In each repository:

```bash
git submodule add --branch main https://github.com/nikolareljin/docforge.git vendor/docforge
cp vendor/docforge/docforge.example.yml .docforge.yml
mkdir -p .github/workflows
cp vendor/docforge/templates/workflow.yml .github/workflows/docs.yml
```

### Step 2: Configure `.docforge.yml`

Edit `.docforge.yml` with your project details:

```yaml
project:
  name: "My API"
  description: "REST API for managing tasks."
  language: "python"

ai:
  provider: "github"   # uses GITHUB_TOKEN automatically
  model: "gpt-4o"

output:
  notebooklm: true
```

### Step 3: Enable NotebookLM Upload in Workflow

Edit `.github/workflows/docs.yml` and uncomment the multi-repo upload block:

```yaml
      - name: "Generate documentation"
        uses: ./vendor/docforge
        with:
          config: .docforge.yml
          only: both

          # Multi-repo NotebookLM upload
          notebooklm_upload: "true"
          notebooklm_project_number: "123456789012"              # Your GCP project number
          notebooklm_notebook_id: "your-notebook-id"              # Your notebook ID
          notebooklm_source_prefix: "${{ github.event.repository.name }}-"  # Auto-prefix
          notebooklm_sa_key: ${{ secrets.NOTEBOOKLM_SA_KEY }}    # Organization secret
```

The key line is:
```yaml
notebooklm_source_prefix: "${{ github.event.repository.name }}-"
```

This automatically uses the repository name as the prefix. For `myapi`, the uploaded
file becomes `myapi-NOTEBOOKLM.md`.

### Step 4: Commit and Push

```bash
git add .docforge.yml .github/workflows/docs.yml vendor/docforge .gitmodules
git commit -m "chore: add docforge documentation generator"
git push
```

On push to `main`, the workflow:
1. Generates `DEVELOPER.md`, `USER_GUIDE.md`, `NOTEBOOKLM.md`
2. Commits them to the repo
3. Uploads `NOTEBOOKLM.md` to your notebook as `myapi-NOTEBOOKLM.md`

---

## Alternative: Config File Approach

Instead of setting inputs in the workflow, configure upload in `.docforge.yml`:

```yaml
notebooklm_upload:
  enabled: true
  project_number: "123456789012"
  notebook_id: "your-notebook-id"
  source_prefix: "myapi-"   # Hardcoded prefix (manual)
```

Then in the workflow, just enable upload without repeating config:

```yaml
      - uses: ./vendor/docforge
        with:
          config: .docforge.yml
          notebooklm_upload: "true"
          notebooklm_sa_key: ${{ secrets.NOTEBOOKLM_SA_KEY }}
```

**Trade-off:** Config file is cleaner but requires manual prefix management per repo.
Workflow input approach is copy-paste across all repos with automatic prefixing.

---

## Verifying Multi-Repo Upload

After pushing to `main` in multiple repos:

1. Go to [notebooklm.google.com](https://notebooklm.google.com) and open your notebook.
2. Click **Sources** in the sidebar.
3. You should see:
   - `myapi-NOTEBOOKLM.md`
   - `myfrontend-NOTEBOOKLM.md`
   - `mylib-NOTEBOOKLM.md`
4. Ask NotebookLM: *"What are all the projects documented here?"* — it will list all three.

---

## Organization-Wide Secrets

Store these as **organization secrets** (Settings → Secrets → Actions → New organization secret)
so all repos can reuse them:

| Secret Name | Value |
|---|---|
| `NOTEBOOKLM_SA_KEY` | Full JSON key from `sa-key.json` |

Then reference in each repo's workflow:

```yaml
notebooklm_sa_key: ${{ secrets.NOTEBOOKLM_SA_KEY }}
```

No per-repo secret configuration needed — all repos share the same service account.

---

## Updating Documentation

Every push to `main` in any repo triggers:
1. **Re-generation** of that repo's docs.
2. **Re-upload** of `{repo}-NOTEBOOKLM.md` to the notebook (overwrites previous version).

NotebookLM automatically re-indexes the updated source. No manual intervention needed.

---

## Querying Across Repos in NotebookLM

Example queries that work across all uploaded docs:

- *"Which projects use Python?"*
- *"Show me all the REST API endpoints across all services."*
- *"What testing frameworks are used in the backend repos?"*
- *"Summarize the deployment process for myapi and myfrontend."*

NotebookLM treats all sources as a unified knowledge base.

---

## Docker Alternative (Local Multi-Repo)

If running locally via Docker and uploading to NotebookLM:

```bash
# Repo A
docker run --rm \
  -v "$(pwd):/repo:ro" \
  -v "$(pwd)/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e NOTEBOOKLM_UPLOAD=true \
  -e NOTEBOOKLM_PROJECT_NUMBER="123456789012" \
  -e NOTEBOOKLM_NOTEBOOK_ID="your-notebook-id" \
  -e NOTEBOOKLM_SOURCE_PREFIX="myapi-" \
  -e NOTEBOOKLM_SA_KEY_JSON="${SA_KEY_JSON}" \
  ghcr.io/nikolareljin/docforge:latest

# Repo B
docker run --rm \
  -v "/path/to/myfrontend:/repo:ro" \
  -v "/path/to/myfrontend/docs:/output" \
  -e GITHUB_TOKEN="${GITHUB_TOKEN}" \
  -e NOTEBOOKLM_UPLOAD=true \
  -e NOTEBOOKLM_PROJECT_NUMBER="123456789012" \
  -e NOTEBOOKLM_NOTEBOOK_ID="your-notebook-id" \
  -e NOTEBOOKLM_SOURCE_PREFIX="myfrontend-" \
  -e NOTEBOOKLM_SA_KEY_JSON="${SA_KEY_JSON}" \
  ghcr.io/nikolareljin/docforge:latest
```

Each repo gets its own prefix. All upload to the same notebook.

---

## Troubleshooting

**"Source already exists with this name"**
NotebookLM uploads **overwrite** existing sources with the same filename. If you see
this error, the prefix is not unique. Ensure `source_prefix` differs per repo.

**"Permission denied" (403)**
The service account needs the **Discovery Engine Editor** role. Verify:
```bash
gcloud projects get-iam-policy "${PROJECT_ID}" \
  --flatten="bindings[].members" \
  --filter="bindings.members:docforge-uploader"
```

**Upload succeeds but source not visible in NotebookLM**
Check the notebook ID is correct. The ID in the URL must match `notebooklm_notebook_id`.

**Shared secret not working across repos**
Organization secrets must be explicitly allowed for each repository. Go to
**Organization Settings → Secrets → Actions → NOTEBOOKLM_SA_KEY → Repository access**
and select "All repositories" or manually add each repo.

---

## Cost Estimation

- **Discovery Engine API**: Free tier includes 1,000 document uploads/month. Each
  docforge run = 1 upload. For 10 repos pushing 5x/day = 1,500 uploads/month = ~$0
  (within free tier).
- **NotebookLM**: Free during beta (as of 2026-02).
- **GitHub Actions**: Compute for doc generation. ~2 minutes per run = negligible
  within free tier (2,000 minutes/month for public repos).

---

## Best Practices

1. **Use organization secrets** — avoid duplicating the SA key across repos.
2. **Use automatic prefixing** — `${{ github.event.repository.name }}-` removes
   manual coordination.
3. **Keep the notebook focused** — don't upload from 100+ repos to one notebook.
   Consider 10-20 related repos per notebook.
4. **Monitor upload failures** — add a Slack/email notification on workflow failure
   so stale docs are caught quickly.
5. **Version your configs** — commit `.docforge.yml` changes with meaningful messages
   so you can track what context the LLM saw when it generated docs.
