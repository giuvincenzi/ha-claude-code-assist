"""How a session's Claude Code process is started: the launch spec of one session.

Kept apart from the app's wiring so it can be tested: the tools and the permissions given to
Claude Code decide what it can do, and what it can read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .claude_process import LaunchSpec
from .config import INTERNAL_MCP_SERVER, Settings
from .mcp_tools import MEMORY_TOOLS, SESSION_HEADER
from .prompt import build_system_prompt
from .sessions import SessionRecord

WEB_TOOLS = ["WebSearch", "WebFetch"]
READ_TOOL = "Read"


def claude_settings(retention_days: int) -> dict[str, Any]:
    """Claude Code settings of every process (see architecture.md and sessions.md).

    - Read refuses everything outside the session's working directory, apart from the files
      Claude Code keeps for the session itself (WebFetch's downloads among them).
    - Claude Code's own cleanup of old transcripts comes a day after ours: we delete a session
      after `retention_days` without messages, and Claude Code does not document which date it
      counts from, so it never removes the messages of a session the panel still lists.
    """
    return {
        "permissions": {"blockReadsOutsideWorkingDirectories": True},
        "cleanupPeriodDays": retention_days + 1,
    }


def builtin_tools(web_search: bool, read_files: bool) -> list[str]:
    """Claude Code's own tools the session gets."""
    return ([READ_TOOL] if read_files else []) + (WEB_TOOLS if web_search else [])


def build_launch_spec(
    record: SessionRecord,
    resume: bool,
    *,
    settings: Settings,
    memory_text: str,
    internal_mcp_url: str,
    workdir: Path,
    config_dir: Path,
) -> LaunchSpec:
    """The launch spec of a session.

    - Resuming uses Claude Code's own session id; a new conversation gets ours.
    - Read is never in the allowed tools: an allow rule would let it read anywhere. It reads
      only the session's working directory and the files Claude Code keeps for the session,
      as Claude Code itself allows (see architecture.md).
    """
    internal: dict[str, Any] = {
        "type": "http",
        "url": internal_mcp_url,
        "headers": {SESSION_HEADER: record.session_id},
    }
    servers = {**settings.mcp_servers, INTERNAL_MCP_SERVER: internal}
    builtin = builtin_tools(record.settings.web_search, record.settings.read_files)
    if resume:
        if record.claude.session_id is None:
            raise ValueError("cannot resume a session Claude Code never reported")
        session_id = record.claude.session_id
    else:
        session_id = record.session_id
    return LaunchSpec(
        session_id=session_id,
        resume=resume,
        model=record.settings.model,
        effort=record.settings.effort,
        system_prompt=build_system_prompt(
            record.source["channel"], memory_text if record.settings.memory_enabled else None),
        mcp_config={"mcpServers": servers},
        builtin_tools=builtin,
        allowed_tools=[f"mcp__{name}" for name in servers] + [t for t in builtin if t != READ_TOOL],
        disallowed_tools=[] if record.settings.memory_enabled else [f"mcp__{INTERNAL_MCP_SERVER}__{t}" for t in MEMORY_TOOLS],
        oauth_token=settings.oauth_token,
        workdir=workdir,
        config_dir=config_dir,
        claude_settings=claude_settings(settings.session_retention.days),
    )
