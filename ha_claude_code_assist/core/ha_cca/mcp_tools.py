"""Internal MCP server `ha_cca`: every tool of the app, named ha_cca_*.

Errors are raised as ToolError: the SDK replaces any other exception with a
generic "Error executing tool", and the model then cannot tell the user why.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from .memory import MemoryLimitError, MemoryStore

SERVER_NAME = "ha_cca"
# Set per session in the MCP configuration given to Claude Code, so a tool
# knows which conversation it was called from.
SESSION_HEADER = "X-HA-CCA-Session"
MEMORY_TOOLS = ("ha_cca_memory_add", "ha_cca_memory_remove", "ha_cca_memory_list")


def _session_id(ctx: Context) -> str | None:
    try:
        headers = ctx.headers
    except ValueError:  # no HTTP request behind the call
        return None
    return (headers or {}).get(SESSION_HEADER.lower())


def _local_now() -> datetime:
    # The Supervisor gives every app the Home Assistant time zone in TZ.
    try:
        return datetime.now(ZoneInfo(os.environ.get("TZ", "UTC")))
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.now(ZoneInfo("UTC"))


def build_mcp_server(
    memory: Callable[[], MemoryStore],
    memory_enabled: Callable[[], bool],
    app_info: Callable[[str | None], str],
) -> MCPServer:
    mcp = MCPServer(name=SERVER_NAME)

    def require_memory() -> MemoryStore:
        if not memory_enabled():
            raise ToolError("Long-term memory is turned off. The user can turn it on in the Settings tab of "
                            "the HA Claude Code Assist panel, under Memory.")
        return memory()

    @mcp.tool(
        name="ha_cca_datetime",
        description="Current date, time, day of the week and time zone: of the home, or of another "
                    "place when time_zone is given as an IANA name such as 'Asia/Tokyo'.",
    )
    def datetime_now(time_zone: str | None = None) -> str:
        now = _local_now()
        if time_zone:
            try:
                now = now.astimezone(ZoneInfo(time_zone))
            except (ZoneInfoNotFoundError, ValueError) as err:
                raise ToolError(f"Unknown time zone '{time_zone}': use an IANA name such as "
                                "'Europe/Rome' or 'America/New_York'.") from err
        return f"{now:%A %Y-%m-%d %H:%M:%S}, time zone {time_zone or now.tzname()} (UTC{now:%z})"

    @mcp.tool(
        name="ha_cca_app_info",
        description="How HA Claude Code Assist works: settings with their current values, "
                    "conversations, long-term memory, the tools of this conversation, how to add "
                    "tools (MCP servers) and how they affect subscription usage.",
    )
    def app_info_tool(ctx: Context) -> str:
        return app_info(_session_id(ctx))

    @mcp.tool(
        name="ha_cca_memory_add",
        description="Save one fact to long-term memory. Use it only when the user explicitly "
                    "asks you to remember something. Returns the id of the new entry.",
    )
    async def memory_add(text: str, ctx: Context) -> str:
        try:
            entry = await require_memory().add(text, created_by="claude", conversation_id=_session_id(ctx))
        except MemoryLimitError as err:
            raise ToolError(f"Not saved. {err}.") from err
        return f"Saved as memory entry {entry.id}."

    @mcp.tool(
        name="ha_cca_memory_remove",
        description="Remove one entry from long-term memory by its id. Use it only when the "
                    "user explicitly asks you to forget something.",
    )
    async def memory_remove(entry_id: int) -> str:
        try:
            await require_memory().remove(entry_id, removed_by="claude")
        except KeyError as err:
            raise ToolError(f"Not removed: there is no memory entry with id {entry_id}. "
                            "Use ha_cca_memory_list to see the current ids.") from err
        return f"Memory entry {entry_id} removed."

    @mcp.tool(
        name="ha_cca_memory_list",
        description="List the current long-term memory entries with their ids.",
    )
    def memory_list() -> str:
        return require_memory().render()

    return mcp
