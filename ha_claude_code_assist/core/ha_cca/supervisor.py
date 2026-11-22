"""The Supervisor's API, as the app calls it (its token comes in the environment)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def call(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 15) -> dict[str, Any]:
    """Calls the Supervisor and returns its answer ({"result": "ok" | "error", ...})."""
    request = urllib.request.Request(
        f"http://supervisor{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['SUPERVISOR_TOKEN']}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as err:
        return json.loads(err.read() or b"{}")
