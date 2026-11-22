"""Assist: Home Assistant's voice assistants talk to the app through its integration
(`custom_components/ha_claude_code_assist`), an Assist conversation agent.

- The integration reaches the core on the Supervisor's internal network. Home Assistant Core
  runs in the host's network, so its requests come from the host's address, as any other
  process of the host would: the address alone proves nothing. Every request carries the token
  the core created (`AssistToken`), which the integration gets through Supervisor discovery.
- A message goes to a voice session (channel "voice"), keyed by the voice device it came from;
  Home Assistant's conversation id is attached to it, as the panel's chat ids are.
- The answer streams back as lines of JSON, so the speech can start before it is complete.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import secrets
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from . import supervisor
from .sessions import SessionManager, TurnError

LOGGER = logging.getLogger(__name__)

# The integration's domain: Home Assistant starts its config flow for the service announced.
DISCOVERY_SERVICE = "ha_claude_code_assist"
CHANNEL = "voice"


class AssistToken:
    """The secret the integration sends with every request: made once, kept in /data."""

    def __init__(self, path: Path) -> None:
        if path.is_file():
            self.value = path.read_text().strip()
        else:
            self.value = secrets.token_urlsafe(32)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(self.value)
            tmp.chmod(0o600)
            os.replace(tmp, path)

    def matches(self, authorization: str | None) -> bool:
        given = (authorization or "").removeprefix("Bearer ").strip()
        return bool(given) and hmac.compare_digest(given.encode(), self.value.encode())


def announce(token: AssistToken, host: str, port: int) -> None:
    """Tells Home Assistant, through the Supervisor, where the app is and its token: Home
    Assistant then offers to set up the integration."""
    body = supervisor.call("POST", "/discovery", {
        "service": DISCOVERY_SERVICE,
        "config": {"host": host, "port": port, "token": token.value},
    })
    if body.get("result") != "ok":
        LOGGER.error("Home Assistant could not be told about the app: %s", body.get("message") or body)


def text_delta(message: dict[str, Any]) -> tuple[str | None, bool]:
    """From a session event: the text the assistant streamed, and whether a new text block of the
    answer starts (the parts of an answer are separated, as they would be when read)."""
    if message.get("type") != "turn_event":
        return None, False
    event = message["event"]
    if event.get("type") != "stream_event":
        return None, False
    inner = event.get("event") or {}
    if inner.get("type") == "content_block_start":
        return None, (inner.get("content_block") or {}).get("type") == "text"
    delta = inner.get("delta") or {}
    if inner.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
        return delta.get("text") or None, False
    return None, False


async def stream_turn(sessions: SessionManager, text: str, conversation_id: str | None,
                      source_key: str, source_name: str | None) -> AsyncIterator[dict[str, Any]]:
    """Runs a voice turn and yields its answer: {"delta": text} as it is written, then
    {"done": true, "error": None | "...", "text": ...} (the whole answer when nothing streamed)."""
    record = await sessions.resolve(CHANNEL, source_key, conversation_id, source_name)
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    stop = sessions.subscribe(lambda message: message.get("session_id") == record.session_id
                              and queue.put_nowait(message))
    turn = asyncio.create_task(sessions.run(record, text))
    streamed = False
    try:
        while True:
            message = asyncio.create_task(queue.get())
            await asyncio.wait({message, turn}, return_when=asyncio.FIRST_COMPLETED)
            if not message.done():
                # The turn ended without our session's last event: it went to a new session
                # (this one closed while the message waited), or it failed before running.
                message.cancel()
                try:
                    result = turn.result()
                except TurnError as err:
                    yield {"done": True, "error": "failed", "text": str(err)}
                    return
                yield {"done": True, "error": "failed" if result.is_error else None,
                       "text": "" if streamed and not result.is_error else result.text}
                return
            event = message.result()
            delta, new_block = text_delta(event)
            if new_block and streamed:
                yield {"delta": "\n\n"}
            if delta:
                streamed = True
                yield {"delta": delta}
            if event.get("type") == "turn_finished":
                error = event.get("error") or ("failed" if event.get("is_error") else None)
                yield {"done": True, "error": error, "text": event["text"] if error or not streamed else ""}
                return
    finally:
        stop()  # the turn itself goes on if Home Assistant stops listening: the session stays whole


def assist_router(sessions: SessionManager, token: AssistToken) -> APIRouter:
    router = APIRouter()

    def refused(request: Request) -> Response | None:
        if token.matches(request.headers.get("authorization")):
            return None
        return JSONResponse({"error": "The token of HA Claude Code Assist is not valid."}, status_code=401)

    @router.get("/api/assist/check")
    async def check(request: Request) -> Response:
        """Lets the integration check the address and the token while it is set up."""
        return refused(request) or JSONResponse({"ok": True})

    @router.post("/api/assist")
    async def assist(request: Request) -> Response:
        if error := refused(request):
            return error
        body = await request.json()
        text = str(body.get("text") or "").strip()
        source = body.get("source") or {}
        if not text or not source.get("key"):
            return JSONResponse({"error": "A message needs its text and its source."}, status_code=400)

        async def lines() -> AsyncIterator[bytes]:
            async for item in stream_turn(sessions, text, body.get("conversation_id"),
                                          str(source["key"]), source.get("name")):
                yield (json.dumps(item) + "\n").encode()

        return StreamingResponse(lines(), media_type="application/x-ndjson")

    return router
