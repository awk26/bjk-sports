"""
portall_client.py
------------------
Thin client for the Portall document-extraction API (document.portall.in),
used to pre-fill the coach Assessment form from an uploaded scanned form,
PDF, or Excel sheet.

Flow: upload_document() queues the file and returns a task_id, then
get_task_status() is polled (from routes/coach.py, driven by the browser)
until status == "completed", at which point `data` is a dict whose keys
line up 1:1 with most of ASSESSMENT_FIELDS in common/models.py.

Uses the PORTALL_API_KEY env var (set it in .env) and PORTALL_BASE_URL
(defaults to https://document.portall.in). If the key is missing or the
API call fails, callers get a PortallError with a message safe to show
the coach -- this never touches assessment data directly, so a failure
here just means "import didn't work", not a broken assessment.
"""

import os
import requests

from common.logs import log

PORTALL_BASE_URL = os.getenv("PORTALL_BASE_URL", "https://document.portall.in").rstrip("/")
PORTALL_API_KEY_UPLOAD = os.getenv("PORTALL_API_KEY_UPLOAD", "")
PORTALL_API_KEY_EXTRACT = os.getenv("PORTALL_API_KEY_EXTRACT", "")


class PortallError(Exception):
    pass





def upload_document(file_storage) -> dict:
    """Uploads a werkzeug FileStorage to the Portall extraction API.

    Returns the parsed JSON response on success, e.g.:
        {"success": true, "task_id": "...", "status": "queued", "poll_url": "..."}
    Raises PortallError with a coach-safe message on any failure.
    """
    if not PORTALL_API_KEY_UPLOAD:
        raise PortallError("Document import is not configured (missing API key).")

    try:
        resp = requests.post(
            f"{PORTALL_BASE_URL}/api/public/upload",
            headers={"X-API-Key": PORTALL_API_KEY_UPLOAD},
            files={"file": (file_storage.filename, file_storage.stream, file_storage.mimetype)},
            timeout=30,
        )
    except requests.RequestException as e:
        log(f"portall_client: upload request failed: {e}")
        raise PortallError("Could not reach the document import service.")

    if resp.status_code >= 400:
        log(f"portall_client: upload returned {resp.status_code}: {resp.text[:300]}")
        raise PortallError("The document import service rejected this file.")

    try:
        data = resp.json()
    except ValueError:
        raise PortallError("The document import service returned an unexpected response.")

    if not data.get("success"):
        raise PortallError(data.get("message") or "Upload failed.")

    return data


def get_task_status(task_id: str) -> dict:
    """Polls the extraction task status. Returns the parsed JSON response
    (success/status/data/...). Raises PortallError on transport failure."""
    if not PORTALL_API_KEY_EXTRACT:
        raise PortallError("Document import is not configured (missing API key).")

    try:
        resp = requests.get(
            f"{PORTALL_BASE_URL}/api/public/status/{task_id}",
            headers={"X-API-Key": PORTALL_API_KEY_EXTRACT},
            timeout=30,
        )
    except requests.RequestException as e:
        log(f"portall_client: status request failed: {e}")
        raise PortallError("Could not reach the document import service.")

    if resp.status_code >= 400:
        log(f"portall_client: status returned {resp.status_code}: {resp.text[:300]}")
        raise PortallError("The document import service could not find this task.")

    try:
        return resp.json()
    except ValueError:
        raise PortallError("The document import service returned an unexpected response.")
