"""What ha_cca_app_info returns: the app's documentation plus its current state.

DOCS.md is the single source of what HA Claude Code Assist is and how it works;
this module only adds what a static file cannot hold: the current settings,
the tools and context of the calling conversation, the memory in use.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config import Settings
from .sessions import SessionRecord


@dataclass(frozen=True)
class AppInfoContext:
    docs: str  # DOCS.md
    settings: Settings
    token: dict[str, Any]
    memory_used: int
    session: SessionRecord | None  # the calling conversation, if known
    session_tools: list[str]


def _on_off(value: bool) -> str:
    return "on" if value else "off"


def _date(iso: str | None) -> str:
    return datetime.fromisoformat(iso).strftime("%Y-%m-%d") if iso else "unknown"


def _tools_summary(tools: list[str]) -> str:
    if not tools:
        return "not known yet (reported when the conversation starts)"
    servers: Counter[str] = Counter()
    builtin = []
    for name in tools:
        if name.startswith("mcp__"):
            servers[name.split("__")[1]] += 1
        else:
            builtin.append(name)
    parts = [f"{count} internal (ha_cca_*)" if server == "ha_cca" else f"{count} from MCP server '{server}'"
             for server, count in sorted(servers.items())]
    if builtin:
        parts.append(f"built-in: {', '.join(builtin)}")
    return f"{len(tools)} tools: " + "; ".join(parts)


def render_status(ctx: AppInfoContext) -> str:
    s = ctx.settings
    token = (f"configured, expires around {_date(ctx.token.get('expires_at'))}"
             if ctx.token.get("configured") else "not configured")
    lines = [
        "# Current state",
        "",
        "Settings (applied to new sessions):",
        f"- Setup token: {token}",
        f"- Model: {s.model}",
        f"- Effort: {s.effort}",
        f"- Web search: {_on_off(s.web_search)}",
        f"- Read files: {_on_off(s.read_files)}",
        f"- MCP servers: {', '.join(sorted(s.mcp_servers)) or 'none'}",
        f"- Session timeout: {int(s.session_timeout.total_seconds() // 60)} minutes",
        f"- Long-term memory: {_on_off(s.memory_enabled)}, {ctx.memory_used} of {s.memory_max_entries} "
        f"entries used, up to {s.memory_max_entry_length} characters each",
    ]
    if ctx.session:
        settings, claude = ctx.session.settings, ctx.session.claude
        lines += [
            "",
            "This session:",
            f"- Model {settings.model}, effort {settings.effort}, web search {_on_off(settings.web_search)}, "
            f"read files {_on_off(settings.read_files)}, long-term memory {_on_off(settings.memory_enabled)}",
            f"- Tools: {_tools_summary(ctx.session_tools)}",
        ]
        if claude.context_tokens:
            window = f" of {claude.context_window:,}" if claude.context_window else ""
            lines.append(f"- Context: {claude.context_tokens:,}{window} tokens")
    return "\n".join(lines) + "\n"


def render_app_info(ctx: AppInfoContext) -> str:
    return f"{ctx.docs.rstrip()}\n\n{render_status(ctx)}"
