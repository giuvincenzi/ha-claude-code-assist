"""Talks to the HA Claude Code Assist app's core, on the Supervisor's internal network."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import aiohttp

CONNECT_TIMEOUT = 10
# An answer can take a while (the assistant may use several tools): only silence ends it.
READ_TIMEOUT = 300


class CannotConnect(Exception):
    """The app does not answer: it is stopped, or the address is wrong."""


class InvalidToken(Exception):
    """The app refused the token."""


class AppClient:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def check(self) -> None:
        """Checks that the app answers and accepts the token."""
        try:
            async with self._session.get(f"{self._base}/api/assist/check", headers=self._headers,
                                         timeout=aiohttp.ClientTimeout(total=CONNECT_TIMEOUT)) as response:
                _raise_for(response)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect from err

    async def converse(self, text: str, conversation_id: str | None, source_key: str, source_name: str | None,
                       language: str) -> AsyncIterator[dict[str, Any]]:
        """Sends a message and yields the answer as the app streams it: {"delta": ...}, then
        {"done": true, "error": ..., "text": ...}."""
        body = {"text": text, "conversation_id": conversation_id, "language": language,
                "source": {"key": source_key, "name": source_name}}
        timeout = aiohttp.ClientTimeout(total=None, connect=CONNECT_TIMEOUT, sock_read=READ_TIMEOUT)
        try:
            async with self._session.post(f"{self._base}/api/assist", json=body, headers=self._headers,
                                          timeout=timeout) as response:
                _raise_for(response)
                async for line in response.content:
                    if line.strip():
                        yield json.loads(line)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect from err


def _raise_for(response: aiohttp.ClientResponse) -> None:
    if response.status == 401:
        raise InvalidToken
    response.raise_for_status()
