"""Upload generated documentation to Google NotebookLM via Discovery Engine API.

Requires google-auth (and requests, used by google-auth's transport):
    pip install google-auth requests

The service account key can be supplied as:
  - A file path via $GOOGLE_APPLICATION_CREDENTIALS (standard gcloud default).
  - A JSON string via $NOTEBOOKLM_SA_KEY_JSON (recommended for CI secrets).
  - Explicit arguments to upload_to_notebooklm() for programmatic use.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx


def _get_access_token(
    sa_key_path: str | None = None,
    sa_key_json: str | None = None,
) -> str:
    """Return a short-lived OAuth2 access token for the Cloud Platform scope."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError as exc:
        raise ImportError(
            "google-auth is required for NotebookLM upload. "
            "Install it with: pip install google-auth requests"
        ) from exc

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]

    # Resolve credentials — explicit args take precedence over env vars.
    if sa_key_json:
        info = json.loads(sa_key_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
    elif sa_key_path:
        creds = service_account.Credentials.from_service_account_file(
            sa_key_path, scopes=scopes
        )
    else:
        env_key_json = os.environ.get("NOTEBOOKLM_SA_KEY_JSON", "")
        env_key_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if env_key_json:
            info = json.loads(env_key_json)
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=scopes
            )
        elif env_key_file and Path(env_key_file).exists():
            creds = service_account.Credentials.from_service_account_file(
                env_key_file, scopes=scopes
            )
        else:
            raise ValueError(
                "No Google credentials found for NotebookLM upload. "
                "Set NOTEBOOKLM_SA_KEY_JSON (JSON string) or "
                "GOOGLE_APPLICATION_CREDENTIALS (file path)."
            )

    creds.refresh(Request())
    return creds.token


def upload_to_notebooklm(
    file_path: str,
    project_number: str,
    notebook_id: str,
    location: str = "global",
    endpoint_location: str = "global",
    sa_key_path: str | None = None,
    sa_key_json: str | None = None,
    timeout: int = 120,
) -> dict:
    """Upload a markdown file to a Google NotebookLM notebook as a source.

    Args:
        file_path:         Local path to the markdown file to upload.
        project_number:    GCP project number (not project ID).
        notebook_id:       NotebookLM notebook ID (from the notebook URL).
        location:          GCP resource location (default: ``global``).
        endpoint_location: Discovery Engine endpoint location (default: ``global``).
        sa_key_path:       Path to a service account JSON key file.
        sa_key_json:       Service account key as a JSON string.
        timeout:           HTTP request timeout in seconds.

    Returns:
        Parsed JSON response from the Discovery Engine upload endpoint.

    Raises:
        ValueError: If required parameters are missing or credentials not found.
        ImportError: If ``google-auth`` is not installed.
        httpx.HTTPStatusError: If the upload request fails.
    """
    if not project_number:
        raise ValueError("project_number is required for NotebookLM upload.")
    if not notebook_id:
        raise ValueError("notebook_id is required for NotebookLM upload.")

    token = _get_access_token(sa_key_path=sa_key_path, sa_key_json=sa_key_json)

    url = (
        f"https://{endpoint_location}-discoveryengine.googleapis.com/upload/v1alpha/"
        f"projects/{project_number}/locations/{location}"
        f"/notebooks/{notebook_id}/sources:uploadFile"
    )

    file_path_obj = Path(file_path)
    content = file_path_obj.read_bytes()

    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Goog-Upload-File-Name": file_path_obj.name,
            "X-Goog-Upload-Protocol": "raw",
            "Content-Type": "text/markdown",
        },
        content=content,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
