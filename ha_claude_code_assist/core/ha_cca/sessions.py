"""Sessions: one Claude Code conversation each, one folder each (SessionStore).

Rules (see .claude/rules/sessions.md):
- a message goes to the session of its conversation id, else to the active
  session of its source (channel + source key), else to a new session;
- a session is active while it has had a turn within the timeout;
- one turn at a time per session; different sessions run in parallel;
- a session whose process is not running is resumed with --resume;
- a session with no messages for longer than the retention period is deleted.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .claude_process import ClaudeProcess, LaunchSpec, ProcessExitedError
from .config import INTERNAL_MCP_SERVER

LOGGER = logging.getLogger(__name__)

REAPER_INTERVAL = 15  # seconds
EXPIRY_INTERVAL = timedelta(hours=1)
TITLE_LENGTH = 80
# Shown instead of Claude Code's own text when the subscription token is rejected.
AUTH_FAILED_MESSAGE = ("Claude Code could not sign in because the setup token was rejected. "
                       "Create a new one with claude setup-token and paste it in Settings.")


SESSION_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SessionSettings:
    """The settings a conversation runs with; never secrets (the record reaches the browser).

    Model, effort, web search and memory are fixed when the conversation starts. MCP servers are
    not: a resumed process gets the configured ones, so `mcp_servers` names those of the
    process's last start (the app's internal server excluded).
    """

    model: str
    effort: str
    web_search: bool
    memory_enabled: bool
    read_files: bool
    mcp_servers: list[str] = field(default_factory=list)


@dataclass
class ClaudeSession:
    """What Claude Code reports about the conversation: only what the panel shows.

    Everything else (messages, tools, models used) is in Claude Code's transcript.
    """

    # The id Claude Code reported for the conversation (its init event); None until it answers.
    # Used for what is Claude Code's: --resume and the transcript's name.
    session_id: str | None = None
    # Size of the context at the last model call, and the model's context window.
    context_tokens: int | None = None
    context_window: int | None = None
    # Totals of the whole conversation, all models together (Claude Code's `modelUsage`).
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    web_search_requests: int | None = None
    cost_usd: float | None = None  # list-price estimate, kept but not shown


@dataclass
class SessionRecord:
    # Ours, created before Claude Code starts: the record's key, its folder, the panel, the
    # memory. A new conversation gives it to Claude Code (--session-id), which reports its own
    # in claude.session_id: two ids for two things, never used one for the other.
    session_id: str
    title: str
    source: dict[str, str]  # {"channel": ..., "key": ..., "name": display name, optional}
    conversation_ids: list[str]
    created_at: str
    last_activity: str
    closed_at: str | None
    settings: SessionSettings
    claude: ClaudeSession

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionRecord:
        return cls(**{**data, "settings": SessionSettings(**data["settings"]),
                      "claude": ClaudeSession(**data["claude"])})


def apply_usage(claude: ClaudeSession, model_usage: dict[str, Any], model: str | None) -> None:
    """Copies a result event's `modelUsage`: the conversation's running totals (they continue
    after --resume), so the latest result replaces the previous one."""
    def total(key: str) -> int:
        return sum(int(m.get(key) or 0) for m in model_usage.values())
    claude.input_tokens = total("inputTokens")
    claude.output_tokens = total("outputTokens")
    claude.cache_read_input_tokens = total("cacheReadInputTokens")
    claude.cache_creation_input_tokens = total("cacheCreationInputTokens")
    claude.web_search_requests = total("webSearchRequests")
    claude.cost_usd = sum(float(m.get("costUSD") or 0) for m in model_usage.values())
    window = (model_usage.get(model or "") or {}).get("contextWindow")
    claude.context_window = window or max(int(m.get("contextWindow") or 0) for m in model_usage.values()) or None


class SessionStore:
    """One folder per session, named after our session id:

        <root>/<session_id>/session.json   the record, written atomically
        <root>/<session_id>/workdir/       Claude Code's working directory (attachments)

    Claude Code reads only its working directory, so the record stays out of its reach.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def folder(self, session_id: str) -> Path:
        if not SESSION_ID.fullmatch(session_id):
            raise ValueError(f"not a session id: {session_id!r}")
        return self._root / session_id

    def workdir(self, session_id: str) -> Path:
        return self.folder(session_id) / "workdir"

    def load(self) -> list[SessionRecord]:
        if not self._root.is_dir():
            return []
        records = []
        for folder in sorted(self._root.iterdir()):
            path = folder / "session.json"
            if not path.is_file():
                LOGGER.warning("Ignoring %s: it has no session.json", folder)
                continue
            # A record that cannot be read must not stop the app: it is left as it is, and logged.
            try:
                records.append(SessionRecord.from_dict(json.loads(path.read_text())))
            except (ValueError, TypeError, KeyError) as err:
                LOGGER.error("Ignoring %s: it cannot be read (%s)", path, err)
        return records

    def save(self, record: SessionRecord) -> None:
        folder = self.folder(record.session_id)
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / "session.json.tmp"
        tmp.write_text(json.dumps(asdict(record), indent=2) + "\n")
        os.replace(tmp, folder / "session.json")

    def remove(self, session_id: str) -> None:
        """Removes the session's folder: its record and its working directory."""
        folder = self.folder(session_id)
        if folder.exists():
            shutil.rmtree(folder)


class TurnError(RuntimeError):
    """The turn could not be completed."""


@dataclass
class TurnResult:
    session_id: str
    text: str
    is_error: bool


@dataclass
class _Runtime:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    process: ClaudeProcess | None = None
    busy: bool = False
    tools: list[str] = field(default_factory=list)  # as reported by Claude Code's init event


# Builds the launch spec of a session's process: (record, resume) -> spec.
SpecBuilder = Callable[[SessionRecord, bool], LaunchSpec]
# Whether Claude Code's transcript of the session exists: (record) -> bool.
TranscriptCheck = Callable[[SessionRecord], bool]
# Removes the files Claude Code keeps for the session: (record) -> paths removed.
ClaudeFilesRemover = Callable[[SessionRecord], list[Path]]
ProcessFactory = Callable[[LaunchSpec], ClaudeProcess]
Listener = Callable[[dict[str, Any]], None]


class SessionManager:
    def __init__(
        self,
        store: SessionStore,
        timeout: Callable[[], timedelta],
        retention: Callable[[], timedelta],
        defaults: Callable[[], SessionSettings],
        spec_builder: SpecBuilder,
        transcript_exists: TranscriptCheck,
        remove_claude_files: ClaudeFilesRemover,
        process_factory: ProcessFactory = ClaudeProcess,
        now: Callable[[], datetime] = _now,
    ) -> None:
        self._store = store
        self._timeout = timeout
        self._retention = retention
        self._defaults = defaults
        self._spec_builder = spec_builder
        self._transcript_exists = transcript_exists
        self._remove_claude_files = remove_claude_files
        self._process_factory = process_factory
        self._now = now
        self._records: dict[str, SessionRecord] = {r.session_id: r for r in store.load()}
        self._runtime: dict[str, _Runtime] = {}
        self._resolve_lock = asyncio.Lock()
        self._listeners: set[Listener] = set()
        self._reaper: asyncio.Task[None] | None = None
        self._expiry: asyncio.Task[list[str]] | None = None
        self._expired_at: datetime | None = None  # when expired sessions were last removed
        # When the subscription token was last rejected; cleared by the next answered turn.
        self.token_rejected_at: str | None = None

    # --- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self._reaper = asyncio.create_task(self._reap_forever())

    async def shutdown(self) -> None:
        """Stops every process; open sessions stay open and are resumed later."""
        for task in (self._reaper, self._expiry):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        for runtime in self._runtime.values():
            if runtime.process is not None:
                await runtime.process.close()

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    # --- queries -------------------------------------------------------------

    def is_active(self, record: SessionRecord) -> bool:
        if record.closed_at is not None:
            return False
        return self._now() - datetime.fromisoformat(record.last_activity) < self._timeout()

    def describe(self, record: SessionRecord) -> dict[str, Any]:
        runtime = self._runtime.get(record.session_id)
        return {
            **asdict(record),
            "active": self.is_active(record),
            "busy": bool(runtime and runtime.busy),
            "process_running": bool(runtime and runtime.process and runtime.process.alive),
        }

    def sessions(self) -> list[dict[str, Any]]:
        records = sorted(self._records.values(), key=lambda r: r.last_activity, reverse=True)
        return [self.describe(r) for r in records]

    def clear_token_rejection(self) -> None:
        """A new token was configured: its state is unknown until the next turn."""
        self.token_rejected_at = None

    def tools(self, session_id: str) -> list[str]:
        """Tools available in the session's running process (empty if not started)."""
        runtime = self._runtime.get(session_id)
        return list(runtime.tools) if runtime else []

    def workdir(self, session_id: str) -> Path:
        """The session's working directory, where its Claude Code process starts."""
        return self._store.workdir(session_id)

    def get(self, session_id: str) -> SessionRecord:
        try:
            return self._records[session_id]
        except KeyError:
            raise KeyError("This session no longer exists.") from None

    # --- turns ---------------------------------------------------------------

    async def send(self, channel: str, source_key: str, conversation_id: str | None, text: str,
                   source_name: str | None = None) -> TurnResult:
        """Routes a message to its session and runs the turn."""
        record = await self.resolve(channel, source_key, conversation_id, source_name)
        return await self.run(record, text)

    async def resolve(self, channel: str, source_key: str, conversation_id: str | None,
                      source_name: str | None = None) -> SessionRecord:
        """The session a message goes to, created if needed."""
        return await self._resolve(channel, source_key, conversation_id, source_name)

    async def run(self, record: SessionRecord, text: str, title: str | None = None,
                  move_if_closed: bool = True) -> TurnResult:
        """Runs one turn; waits for the session's previous turn to finish.

        `title` names a new session (the message by default). A message whose session closed
        while it waited goes to a new session, unless `move_if_closed` is False: a message with
        files attached to this session must not, as the new session cannot read them.
        """
        runtime = self._runtime.setdefault(record.session_id, _Runtime())
        async with runtime.lock:
            if record.closed_at is not None:
                if not move_if_closed:
                    raise TurnError("This session ended before your message was sent. Attach the files again.")
                # Closed (or deleted) while this message was waiting: it starts a new session.
                source = record.source
                record = await self._resolve(source["channel"], source["key"], None)
                runtime = self._runtime.setdefault(record.session_id, _Runtime())
                async with runtime.lock:
                    return await self._run_locked(record, runtime, text, title)
            return await self._run_locked(record, runtime, text, title)

    async def _run_locked(self, record: SessionRecord, runtime: _Runtime, text: str,
                          title: str | None) -> TurnResult:
        runtime.busy = True
        self._publish_session(record)
        try:
            return await self._run_turn(record, runtime, text, title)
        finally:
            runtime.busy = False
            self._publish_session(record)

    async def close(self, session_id: str, reason: str = "manual") -> None:
        record = self.get(session_id)
        runtime = self._runtime.get(session_id)
        if runtime is not None and runtime.busy:
            raise TurnError("The assistant is still answering. Wait for the answer, then end the session.")
        await self._close(record, reason)

    async def delete(self, session_id: str) -> None:
        """Closes the session, then removes its folder (record and working directory) and the
        files Claude Code keeps for it.

        Refused while a turn runs or waits. Holding the session's turn lock, no turn can start
        meanwhile; a message that arrives during the deletion finds the session closed and
        starts a new one. The record goes last: if the deletion is interrupted (the app stops),
        the session is still listed and the next deletion finishes it, never leaving files
        nobody can remove.
        """
        record = self.get(session_id)
        runtime = self._runtime.setdefault(session_id, _Runtime())
        if runtime.lock.locked():
            raise TurnError("The assistant is still answering. Wait for the answer, then delete the session.")
        async with runtime.lock, self._resolve_lock:
            await self._close(record, "deleted")
            removed = await asyncio.to_thread(self._remove_claude_files, record)
            await asyncio.to_thread(self._store.remove, session_id)
            del self._records[session_id]
        LOGGER.info("Session %s deleted with Claude Code's files: %s", session_id,
                    ", ".join(str(p) for p in removed) or "none")
        self._publish({"type": "session_deleted", "session_id": session_id})

    def is_expired(self, record: SessionRecord) -> bool:
        """No messages for longer than the retention period; an active session never is."""
        if self.is_active(record) or self._busy(record):
            return False
        return self._now() - datetime.fromisoformat(record.last_activity) > self._retention()

    async def remove_expired(self) -> list[str]:
        """Deletes the expired sessions exactly as Delete does. Returns their session ids."""
        self._expired_at = self._now()
        removed = []
        for record in [r for r in self._records.values() if self.is_expired(r)]:
            try:
                await self.delete(record.session_id)
            except (KeyError, TurnError):  # deleted meanwhile, or a turn started meanwhile
                continue
            LOGGER.info("Session %s deleted: no messages for more than %d days",
                        record.session_id, self._retention().days)
            removed.append(record.session_id)
        return removed

    def schedule_expiry(self) -> None:
        """Removes the expired sessions in the background, now (the retention period changed)."""
        if self._expiry is None or self._expiry.done():
            self._expiry = asyncio.create_task(self.remove_expired())

    async def _resolve(self, channel: str, source_key: str, conversation_id: str | None,
                       source_name: str | None = None) -> SessionRecord:
        async with self._resolve_lock:
            for record in self._records.values():
                if record.closed_at is None and not self.is_active(record) and not self._busy(record):
                    await self._close(record, "timeout")
            if conversation_id is not None:
                for record in self._records.values():
                    if conversation_id in record.conversation_ids and self.is_active(record):
                        return record
            for record in self._records.values():
                same_source = record.source["channel"] == channel and record.source["key"] == source_key
                if same_source and self.is_active(record):
                    if conversation_id is not None:
                        record.conversation_ids.append(conversation_id)
                        self._save(record)
                    return record
            return self._create(channel, source_key, conversation_id, source_name)

    def _create(self, channel: str, source_key: str, conversation_id: str | None,
                source_name: str | None) -> SessionRecord:
        session_id = str(uuid.uuid4())
        defaults = self._defaults()
        now = self._now().isoformat()
        source = {"channel": channel, "key": source_key}
        if source_name:
            source["name"] = source_name
        record = SessionRecord(
            session_id=session_id,
            title="",
            source=source,
            conversation_ids=[conversation_id or session_id],
            created_at=now,
            last_activity=now,
            closed_at=None,
            settings=defaults,
            claude=ClaudeSession(),
        )
        self._records[session_id] = record
        self._save(record)
        LOGGER.info("New session %s for %s/%s", session_id, channel, source_key)
        return record

    async def _run_turn(self, record: SessionRecord, runtime: _Runtime, text: str,
                        title: str | None) -> TurnResult:
        session_id = record.session_id
        if runtime.process is None or not runtime.process.alive:
            await asyncio.to_thread(self._store.workdir(session_id).mkdir, parents=True, exist_ok=True)
            resume = record.claude.session_id is not None and self._transcript_exists(record)
            spec = self._spec_builder(record, resume)
            record.settings.mcp_servers = [name for name in spec.mcp_config.get("mcpServers", {})
                                           if name != INTERNAL_MCP_SERVER]
            runtime.process = self._process_factory(spec)
            await runtime.process.start()
        if not record.title:
            record.title = " ".join((title or text).split())[:TITLE_LENGTH]
        self._publish({"type": "turn_started", "session_id": session_id, "text": text})
        result: dict[str, Any] | None = None
        auth_failed = False
        last_model: str | None = None
        try:
            async for event in runtime.process.turn(text):
                if event.get("type") == "system" and event.get("subtype") == "init":
                    runtime.tools = list(event.get("tools") or [])
                    reported = event.get("session_id")
                    if reported and reported != record.claude.session_id:
                        record.claude.session_id = reported
                        self._save(record)
                if event.get("type") == "assistant":
                    usage = (event.get("message") or {}).get("usage") or {}
                    if usage:
                        record.claude.context_tokens = sum(usage.get(k) or 0 for k in (
                            "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
                        last_model = (event.get("message") or {}).get("model")
                if event.get("type") == "assistant" and event.get("error") == "authentication_failed":
                    auth_failed = True
                if event.get("type") == "result":
                    result = event
                self._publish({"type": "turn_event", "session_id": session_id, "event": event})
        except ProcessExitedError as err:
            LOGGER.error("Session %s: Claude Code stopped (%s)", session_id, err.detail or "no detail")
            runtime.process = None
            await self._close(record, "process_exited")
            self._publish({"type": "turn_finished", "session_id": session_id, "is_error": True, "text": str(err)})
            raise TurnError(str(err)) from err
        assert result is not None
        if result.get("modelUsage"):
            apply_usage(record.claude, result["modelUsage"], last_model)
        record.last_activity = self._now().isoformat()
        self._save(record)
        is_error = bool(result.get("is_error")) or result.get("subtype") != "success"
        answer = result.get("result") or "; ".join(result.get("errors") or []) or result.get("subtype", "")
        error = None
        if auth_failed or result.get("api_error_status") == 401:
            is_error, error = True, "authentication_failed"
            LOGGER.error("Session %s: the Claude subscription token was rejected: %s", session_id, answer)
            answer = AUTH_FAILED_MESSAGE
            self.token_rejected_at = self._now().isoformat()
        elif not is_error:
            self.token_rejected_at = None
        self._publish({"type": "turn_finished", "session_id": session_id, "is_error": is_error,
                       "error": error, "text": answer})
        return TurnResult(session_id=session_id, text=answer, is_error=is_error)

    # --- closing -------------------------------------------------------------

    def _busy(self, record: SessionRecord) -> bool:
        runtime = self._runtime.get(record.session_id)
        return bool(runtime and runtime.busy)

    async def _close(self, record: SessionRecord, reason: str) -> None:
        runtime = self._runtime.pop(record.session_id, None)
        if runtime is not None and runtime.process is not None:
            await runtime.process.close()
        if record.closed_at is None:
            record.closed_at = self._now().isoformat()
            self._save(record)
            LOGGER.info("Session %s closed (%s)", record.session_id, reason)
        self._publish_session(record)

    async def _reap_forever(self) -> None:
        """Closes the sessions past their timeout; removes the expired ones at start and then
        every hour."""
        while True:
            if self._expired_at is None or self._now() - self._expired_at >= EXPIRY_INTERVAL:
                await self.remove_expired()
            await asyncio.sleep(REAPER_INTERVAL)
            async with self._resolve_lock:
                for record in list(self._records.values()):
                    if record.closed_at is None and not self.is_active(record) and not self._busy(record):
                        await self._close(record, "timeout")

    # --- persistence and events ---------------------------------------------

    def _save(self, record: SessionRecord) -> None:
        if record.session_id in self._records:  # a deleted session is not written again
            self._store.save(record)

    def _publish(self, message: dict[str, Any]) -> None:
        for listener in list(self._listeners):
            listener(message)

    def _publish_session(self, record: SessionRecord) -> None:
        self._publish({"type": "session_updated", "session": self.describe(record)})
