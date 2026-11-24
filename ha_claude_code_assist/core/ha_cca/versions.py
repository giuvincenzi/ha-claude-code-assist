"""The versions of the app and of its integration.

Both come from the same release, whose number is written by the release script in the app's
`config.yaml` and the integration's `manifest.json`: the app reads its own from the Supervisor,
the integration sends its own with every request. They are meant to be the same; when they are
not, the panel and Assist say which one to update.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# The integration's version, sent with every request; integrations before 0.3.0 send none.
INTEGRATION_VERSION_HEADER = "X-HA-CCA-Integration-Version"
# The app's version, sent back with every answer to the integration.
APP_VERSION_HEADER = "X-HA-CCA-App-Version"

INTEGRATION_OUTDATED = "integration_outdated"
APP_OUTDATED = "app_outdated"


def _number(version: str | None) -> tuple[int, ...]:
    """A release number as numbers to compare; anything else counts as the oldest."""
    try:
        return tuple(int(part) for part in (version or "").split("."))
    except ValueError:
        return (0,)


def problem(app: str | None, integration: str | None) -> str | None:
    """Which side is out of date, or None when they match. `integration` is None for one that
    does not report its version (before 0.3.0); an unknown app version decides nothing."""
    if app is None or app == integration:
        return None
    return APP_OUTDATED if _number(app) < _number(integration) else INTEGRATION_OUTDATED


def problem_message(app: str | None, integration: str | None) -> str | None:
    """What the user reads or hears when the versions do not match."""
    which = problem(app, integration)
    if which is None:
        return None
    if which == APP_OUTDATED:
        return (f"The HA Claude Code Assist app, version {app}, is older than its integration, version "
                f"{integration}. Update the app in Settings > Apps.")
    version = f", version {integration}," if integration else ""
    return (f"The HA Claude Code Assist integration{version} is older than the app, version {app}. "
            "Update the integration in the Marketplace or HACS, then restart Home Assistant.")


class IntegrationVersion:
    """The version of the integration that last talked to the app, kept in /data so the panel
    knows it after a restart too. Not known until the integration first talks to the app."""

    def __init__(self, path: Path) -> None:
        self._path = path
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            data = None
        self.known = data is not None
        self.version: str | None = data["version"] if data else None

    def report(self, version: str | None) -> bool:
        """Records the version of a request; True when it changed."""
        if self.known and version == self.version:
            return False
        self.known, self.version = True, version
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": version}) + "\n")
        os.replace(tmp, self._path)
        return True
