"""ASGI app of the core: panel (HTTP + WebSocket) and internal MCP endpoint."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import socket
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from . import access
from .app_info import AppInfoContext, render_app_info
from .assist import AssistToken, announce, assist_router
from .attachment_routes import attachment_router
from .claude_process import LaunchSpec
from .config import SettingsStore
from .launch import build_launch_spec
from .mcp_tools import build_mcp_server
from .memory import MemoryStore
from .panel import Panel
from .sessions import SessionManager, SessionRecord, SessionSettings, SessionStore
from .transcripts import Transcripts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger("ha_cca")

PORT = 8099

DATA_DIR = Path(os.environ.get("HA_CCA_DATA_DIR", "/data"))
WEB_DIR = Path(os.environ.get("HA_CCA_WEB_DIR", "/opt/web"))
DOCS_FILE = Path(os.environ.get("HA_CCA_DOCS_FILE", "/opt/docs/DOCS.md"))
CLAUDE_CONFIG_DIR = DATA_DIR / "claude"
SESSIONS_DIR = DATA_DIR / "sessions"  # one folder per session (SessionStore)

settings_store = SettingsStore(DATA_DIR / "options.json", DATA_DIR / "token.json")
memory_store = MemoryStore(
    DATA_DIR / "memory",
    max_entries=settings_store.settings.memory_max_entries,
    max_entry_length=settings_store.settings.memory_max_entry_length,
)
transcripts = Transcripts(CLAUDE_CONFIG_DIR)
assist_token = AssistToken(DATA_DIR / "assist_token")


session_store = SessionStore(SESSIONS_DIR)


def launch_spec(record: SessionRecord, resume: bool) -> LaunchSpec:
    return build_launch_spec(
        record, resume,
        settings=settings_store.settings,
        memory_text=memory_store.render(),
        internal_mcp_url=f"http://127.0.0.1:{PORT}{access.MCP_PATH}",
        workdir=session_store.workdir(record.session_id),
        config_dir=CLAUDE_CONFIG_DIR,
    )


def transcript_exists(record: SessionRecord) -> bool:
    claude_id = record.claude.session_id
    return claude_id is not None and transcripts.exists(session_store.workdir(record.session_id), claude_id)


session_manager = SessionManager(
    session_store,
    timeout=lambda: settings_store.settings.session_timeout,
    retention=lambda: settings_store.settings.session_retention,
    defaults=lambda: SessionSettings(
        model=settings_store.settings.model,
        effort=settings_store.settings.effort,
        web_search=settings_store.settings.web_search,
        memory_enabled=settings_store.settings.memory_enabled,
        read_files=settings_store.settings.read_files,
    ),
    spec_builder=launch_spec,
    transcript_exists=transcript_exists,
    remove_claude_files=lambda record: transcripts.remove_project(session_store.workdir(record.session_id)),
)


def apply_settings(changes: dict[str, Any]) -> None:
    if "claude_code_oauth_token" in changes:
        session_manager.clear_token_rejection()
    if "session_retention_days" in changes:
        session_manager.schedule_expiry()  # a shorter period applies right away
    memory_store.max_entries = settings_store.settings.memory_max_entries
    memory_store.max_entry_length = settings_store.settings.memory_max_entry_length


claude_code_version: str | None = None


def status() -> dict[str, Any]:
    sessions = session_manager.sessions()
    return {
        "claude_code_version": claude_code_version,
        "token": settings_store.token_status(),
        "token_rejected_at": session_manager.token_rejected_at,
        "mcp_servers": sorted(settings_store.settings.mcp_servers),
        "active_sessions": sum(1 for s in sessions if s["active"]),
    }


def app_info(session_id: str | None) -> str:
    session = None
    if session_id:
        try:
            session = session_manager.get(session_id)
        except KeyError:
            session = None
    return render_app_info(AppInfoContext(
        docs=DOCS_FILE.read_text(),
        settings=settings_store.settings,
        token=settings_store.token_status(),
        memory_used=len(memory_store.entries()),
        session=session,
        session_tools=session_manager.tools(session_id) if session_id else [],
    ))


panel = Panel(session_manager, memory_store, settings_store, transcripts, apply_settings, status)
mcp = build_mcp_server(
    memory=lambda: memory_store,
    memory_enabled=lambda: settings_store.settings.memory_enabled,
    app_info=app_info,
)


class ClientFilter:
    """Rejects connections that do not come from the allowed client."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            host = (scope.get("client") or ("", 0))[0]
            if not access.allowed(scope["path"], host):
                LOGGER.warning("Rejected %s %s from %s", scope["type"], scope["path"], host)
                if scope["type"] == "http":
                    await JSONResponse({"error": "forbidden"}, status_code=403)(scope, receive, send)
                else:
                    await send({"type": "websocket.close", "code": 1008})
                return
        await self.app(scope, receive, send)


async def read_claude_code_version() -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await proc.communicate()
        return out.decode().strip() or None
    except FileNotFoundError:
        return None


async def announce_to_home_assistant() -> None:
    """Supervisor discovery: Home Assistant offers to set up the integration for Assist. If it
    fails, the app still works, and the integration can be set up by hand."""
    try:
        await asyncio.to_thread(announce, assist_token, socket.gethostname(), PORT)
    except OSError as err:
        LOGGER.error("Home Assistant could not be told about the app: %s", err)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global claude_code_version
    claude_code_version = await read_claude_code_version()
    # The MCP session manager must run for the lifetime of the app; mounted
    # sub-app lifespans are not run by FastAPI.
    async with mcp.session_manager.run():
        session_manager.start()
        await announce_to_home_assistant()
        try:
            yield
        finally:
            await session_manager.shutdown()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(attachment_router(session_manager))
app.include_router(assist_router(session_manager, assist_token))


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    return status()


@app.websocket("/ws")
async def websocket(ws: WebSocket) -> None:
    # Set by the Supervisor's Ingress proxy, the only allowed client.
    await panel.serve(ws, ws.headers.get("x-remote-user-id") or "unknown",
                      ws.headers.get("x-remote-user-display-name") or ws.headers.get("x-remote-user-name"))


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


if (WEB_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")

# Mounted last: it only serves the MCP path; every other path is matched above.
app.mount("/", mcp.streamable_http_app(streamable_http_path=access.MCP_PATH, stateless_http=True, json_response=True))

app.add_middleware(ClientFilter)
