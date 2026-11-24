"""Talks to the HA Claude Code Assist app's core, on the Supervisor's internal network."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import aiohttp
from awesomeversion import AwesomeVersion

from .const import APP_VERSION_HEADER, INTEGRATION_VERSION_HEADER

CONNECT_TIMEOUT = 10
# An answer can take a while (the assistant may use several tools): only silence ends it.
READ_TIMEOUT = 300

APP_OUTDATED_MESSAGE = ("The HA Claude Code Assist app is older than its integration. Update the app in "
                        "Settings > Apps.")


class CannotConnect(Exception):
    """The app does not answer: it is stopped, or the address is wrong."""


class InvalidToken(Exception):
    """The app refused the token."""


class AppRefused(Exception):
    """The app could not take the message; the exception's text says why, for the user."""


def app_outdated(app_version: str | None, version: str) -> bool:
    """Whether the app is older than this integration. An app that does not report its version
    is older: apps report it since 0.3.0."""
    return app_version is None or AwesomeVersion(app_version) < AwesomeVersion(version)


class AppClient:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str, version: str,
                 on_app_version: Callable[[str | None], None] | None = None) -> None:
        """`version` is this integration's own; `on_app_version` hears the app's, from every answer."""
        self._session = session
        self._base = f"http://{host}:{port}"
        self._headers = {"Authorization": f"Bearer {token}", INTEGRATION_VERSION_HEADER: version}
        self._version = version
        self._on_app_version = on_app_version

    async def check(self) -> None:
        """Checks that the app answers and accepts the token."""
        try:
            async with self._session.get(f"{self._base}/api/assist/check", headers=self._headers,
                                         timeout=aiohttp.ClientTimeout(total=CONNECT_TIMEOUT)) as response:
                await self._raise_for(response)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect from err

    async def converse(self, ha_input: dict[str, Any], conversation_id: str, source_key: str,
                       source_name: str | None) -> AsyncIterator[dict[str, Any]]:
        """Sends what Home Assistant gave the agent and yields the answer as the app streams it:
        {"delta": ...}, then {"done": true, "error": ..., "text": ...}."""
        body = {"conversation_id": conversation_id, "source": {"key": source_key, "name": source_name},
                "input": ha_input}
        timeout = aiohttp.ClientTimeout(total=None, connect=CONNECT_TIMEOUT, sock_read=READ_TIMEOUT)
        try:
            async with self._session.post(f"{self._base}/api/assist", json=body, headers=self._headers,
                                          timeout=timeout) as response:
                await self._raise_for(response)
                async for line in response.content:
                    if line.strip():
                        yield json.loads(line)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect from err

    async def _raise_for(self, response: aiohttp.ClientResponse) -> None:
        app_version = response.headers.get(APP_VERSION_HEADER)
        if self._on_app_version is not None:
            self._on_app_version(app_version)
        if response.status == 401:
            raise InvalidToken
        if response.status == 400:
            # A message the app could not take: an app older than this integration does not
            # know how it is sent; otherwise the app says why.
            if app_outdated(app_version, self._version):
                raise AppRefused(APP_OUTDATED_MESSAGE)
            try:
                error = (await response.json()).get("error")
            except (aiohttp.ContentTypeError, json.JSONDecodeError):
                error = None
            raise AppRefused(error or "HA Claude Code Assist could not take the message.")
        response.raise_for_status()
