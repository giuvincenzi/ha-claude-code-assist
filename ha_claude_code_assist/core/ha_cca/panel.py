"""Panel channel: one WebSocket per browser tab, JSON request/response plus pushed events.

Client → server: {"id": n, "type": "<command>", ...}
Server → client: {"id": n, "type": "result", "success": bool, "result" | "error"}
                 {"type": "event", "event": {...}}   (sessions, turns, memory, settings)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from . import attachments
from .config import EFFORTS, MODELS, SettingsStore
from .mcp_check import check_server
from .memory import MemoryStore
from .sessions import SessionManager
from .transcripts import Transcripts

LOGGER = logging.getLogger(__name__)

CHANNEL = "panel"
EDITABLE_SETTINGS = {
    "claude_code_oauth_token", "model", "effort", "web_search", "read_files", "mcp_servers",
    "session_timeout_minutes", "session_retention_days", "memory_enabled", "memory_max_entries", "memory_max_entry_length",
}


class Panel:
    def __init__(
        self,
        sessions: SessionManager,
        memory: MemoryStore,
        settings: SettingsStore,
        transcripts: Transcripts,
        on_settings_changed: Callable[[dict[str, Any]], None],
        status: Callable[[], dict[str, Any]],
    ) -> None:
        self._sessions = sessions
        self._memory = memory
        self._settings = settings
        self._transcripts = transcripts
        self._on_settings_changed = on_settings_changed
        self._status = status
        # Every open panel, to tell all of them when the settings change.
        self._outboxes: set[asyncio.Queue[dict[str, Any]]] = set()

    async def serve(self, ws: WebSocket, user_id: str, user_name: str | None) -> None:
        await ws.accept()
        outbox: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._outboxes.add(outbox)
        unsubscribe = [
            self._sessions.subscribe(lambda message: outbox.put_nowait({"type": "event", "event": message})),
            self._memory.subscribe(lambda: outbox.put_nowait({"type": "event", "event": {"type": "memory_changed"}})),
        ]
        writer = asyncio.create_task(self._write(ws, outbox))
        tasks: set[asyncio.Task[None]] = set()
        try:
            while True:
                request = await ws.receive_json()
                task = asyncio.create_task(self._handle(request, (user_id, user_name), outbox))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
        except WebSocketDisconnect:
            pass
        finally:
            self._outboxes.discard(outbox)
            for stop in unsubscribe:
                stop()
            writer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await writer

    async def _write(self, ws: WebSocket, outbox: asyncio.Queue[dict[str, Any]]) -> None:
        while True:
            await ws.send_json(await outbox.get())

    async def _handle(self, request: dict[str, Any], user: tuple[str, str | None],
                      outbox: asyncio.Queue[dict[str, Any]]) -> None:
        request_id = request.get("id")
        handler: Callable[..., Awaitable[Any]] | None = getattr(
            self, "_cmd_" + str(request.get("type", "")).replace("/", "_"), None)
        try:
            if handler is None:
                raise ValueError(f"unknown command {request.get('type')!r}")
            result = await handler(request, user)
            outbox.put_nowait({"id": request_id, "type": "result", "success": True, "result": result})
        except Exception as err:  # every error goes back to the client that asked
            if not isinstance(err, (ValueError, KeyError, RuntimeError)):
                LOGGER.exception("Panel command %s failed", request.get("type"))
            message = err.args[0] if isinstance(err, KeyError) and err.args else str(err)
            outbox.put_nowait({"id": request_id, "type": "result", "success": False, "error": message})

    # --- chat and sessions --------------------------------------------------

    async def _cmd_chat_prepare(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        """The session the next message goes to, created if needed, so the files attached to
        the message can be uploaded into it before the message is sent."""
        self._require_token()
        user_id, user_name = user
        record = await self._sessions.resolve(CHANNEL, user_id, request.get("conversation_id"), user_name)
        if not record.settings.read_files:
            raise ValueError("This session cannot open files. Turn on Read files in Tools, then start a new session.")
        # A session without messages is deleted by the panel if the upload fails.
        return {"session_id": record.session_id, "empty": not record.title}

    async def _cmd_chat_send(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        text = str(request.get("text", "")).strip()
        names = [str(name) for name in request.get("attachments") or []]
        if not text and not names:
            raise ValueError("Write a message first.")
        self._require_token()
        # The panel generates its own conversation id for every chat thread.
        user_id, user_name = user
        record = await self._sessions.resolve(CHANNEL, user_id, request.get("conversation_id"), user_name)
        workdir = self._sessions.workdir(record.session_id)
        missing = [name for name in names if attachments.path(workdir, name) is None]
        if missing:
            raise ValueError(f'The attached file "{missing[0]}" did not reach the assistant. Attach it again.')
        message = attachments.message(text, workdir, names)
        task = asyncio.create_task(self._sessions.run(
            record, message, title=text or ", ".join(names), move_if_closed=not names))
        task.add_done_callback(_log_turn_failure)
        return {"session_id": record.session_id}

    def _require_token(self) -> None:
        if not self._settings.settings.oauth_token:
            raise ValueError("Paste your setup token in Settings first.")

    async def _cmd_sessions_list(self, request: dict[str, Any], user: tuple[str, str | None]) -> list[dict[str, Any]]:
        return self._sessions.sessions()

    async def _cmd_sessions_history(self, request: dict[str, Any], user: tuple[str, str | None]) -> list[dict[str, Any]]:
        session_id = str(request["session_id"])
        claude_id = self._sessions.get(session_id).claude.session_id
        if claude_id is None:  # Claude Code has not answered yet: no transcript
            return []
        return await asyncio.to_thread(self._transcripts.messages, self._sessions.workdir(session_id), claude_id)

    async def _cmd_sessions_close(self, request: dict[str, Any], user: tuple[str, str | None]) -> None:
        await self._sessions.close(str(request["session_id"]))

    async def _cmd_sessions_delete(self, request: dict[str, Any], user: tuple[str, str | None]) -> None:
        await self._sessions.delete(str(request["session_id"]))

    # --- memory ---------------------------------------------------------------

    async def _cmd_memory_list(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        return {
            "entries": [asdict(e) for e in self._memory.entries()],
            "max_entries": self._memory.max_entries,
            "max_entry_length": self._memory.max_entry_length,
        }

    async def _cmd_memory_add(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        return asdict(await self._memory.add(str(request.get("text", "")), created_by="user"))

    async def _cmd_memory_update(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        return asdict(await self._memory.update(int(request["entry_id"]), str(request.get("text", ""))))

    async def _cmd_memory_remove(self, request: dict[str, Any], user: tuple[str, str | None]) -> None:
        await self._memory.remove(int(request["entry_id"]), removed_by="user")

    # --- settings and status ------------------------------------------------

    async def _cmd_settings_get(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        return self._settings_view()

    async def _cmd_settings_update(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        changes = request.get("changes") or {}
        unknown = set(changes) - EDITABLE_SETTINGS
        if unknown:
            raise ValueError(f"The panel cannot change {', '.join(sorted(unknown))}.")
        await self._settings.update(changes)
        self._on_settings_changed(changes)
        # After the change is applied, so every panel reads the new state (status bar included).
        for outbox in self._outboxes:
            outbox.put_nowait({"type": "event", "event": {"type": "settings_changed"}})
        return self._settings_view()

    async def _cmd_mcp_check(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        """Connects to every saved MCP server, in parallel, and reports what each answered."""
        servers = self._settings.settings.mcp_servers
        results = await asyncio.gather(*(asyncio.to_thread(check_server, config) for config in servers.values()))
        return dict(zip(servers, results, strict=True))

    async def _cmd_status_get(self, request: dict[str, Any], user: tuple[str, str | None]) -> dict[str, Any]:
        return self._status()

    def _settings_view(self) -> dict[str, Any]:
        raw = self._settings.raw
        return {
            "values": {key: raw.get(key) for key in EDITABLE_SETTINGS - {"claude_code_oauth_token"}},
            "token": {**self._settings.token_status(), "rejected_at": self._sessions.token_rejected_at},
            "choices": {"model": list(MODELS), "effort": list(EFFORTS)},
        }


def _log_turn_failure(task: asyncio.Task[Any]) -> None:
    if not task.cancelled() and task.exception() is not None:
        LOGGER.warning("Turn failed: %s", task.exception())
