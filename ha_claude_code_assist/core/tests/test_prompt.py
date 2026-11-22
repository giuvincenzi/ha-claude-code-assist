from datetime import timedelta

from ha_cca.app_info import AppInfoContext, render_app_info
from ha_cca.config import parse_options
from ha_cca.prompt import build_system_prompt
from ha_cca.sessions import ClaudeSession, SessionRecord, SessionSettings


def test_prompt_with_memory():
    prompt = build_system_prompt("panel", "- [1] The study is Office")
    assert "This conversation comes from: the chat in the HA Claude Code Assist panel." in prompt
    assert "<memory>" in prompt and "- [1] The study is Office" in prompt


def test_prompt_without_memory():
    prompt = build_system_prompt("panel", None)
    assert "<memory" not in prompt and "ha_cca_memory_add" not in prompt


def test_prompt_is_stable():
    assert build_system_prompt("panel", "(no entries)") == build_system_prompt("panel", "(no entries)")


def test_app_info_is_the_docs_plus_current_state():
    settings = parse_options({"model": "sonnet", "web_search": True, "session_timeout_minutes": 9,
                              "mcp_servers": '{"mcpServers": {"ha-mcp": {"type": "http", "url": "http://x"}}}'})
    session = SessionRecord(
        session_id="8f14e45f-ceea-467a-9575-1f0a2f8a1c11", title="hi", source={"channel": "panel", "key": "u"}, conversation_ids=["c"], created_at="2026-01-01T00:00:00+00:00",
        last_activity="2026-01-01T00:00:00+00:00", closed_at=None,
        settings=SessionSettings("haiku", "low", web_search=False, memory_enabled=True, read_files=True, mcp_servers=["ha-mcp"]),
        claude=ClaudeSession("54476395-c998-4b98-9deb-e00441e3d393", context_tokens=1234, context_window=1000000))
    info = render_app_info(AppInfoContext(
        docs="# HA Claude Code Assist\n\nThe documentation.\n", settings=settings, token={"configured": False},
        memory_used=3, session=session,
        session_tools=["WebSearch", "mcp__ha_cca__ha_cca_datetime", "mcp__ha-mcp__ha_search", "mcp__ha-mcp__ha_get_state"],
    ))
    assert info.startswith("# HA Claude Code Assist\n\nThe documentation.\n\n# Current state")
    assert "- Model: sonnet" in info and "- Session timeout: 9 minutes" in info and "- MCP servers: ha-mcp" in info
    assert "- Model haiku, effort low, web search off, read files on, long-term memory on" in info
    assert "4 tools: 2 from MCP server 'ha-mcp'; 1 internal (ha_cca_*); built-in: WebSearch" in info
    assert "3 of 100 entries used" in info and "- Context: 1,234 of 1,000,000 tokens" in info
    assert "- Setup token: not configured" in info
    assert settings.session_timeout == timedelta(minutes=9)


def test_app_info_context_without_window():
    settings = parse_options({})
    session = SessionRecord(
        session_id="8f14e45f-ceea-467a-9575-1f0a2f8a1c11", title="", source={"channel": "panel", "key": "u"}, conversation_ids=["c"], created_at="2026-01-01T00:00:00+00:00",
        last_activity="2026-01-01T00:00:00+00:00", closed_at=None,
        settings=SessionSettings("haiku", "low", False, True, True),
        claude=ClaudeSession("54476395-c998-4b98-9deb-e00441e3d393", context_tokens=42))
    info = render_app_info(AppInfoContext(docs="# Docs\n", settings=settings, token={"configured": True},
                                          memory_used=0, session=session, session_tools=[]))
    assert "- Context: 42 tokens" in info and "not known yet" in info


def test_app_info_before_the_first_answer_has_no_context_line():
    settings = parse_options({})
    session = SessionRecord(
        session_id="8f14e45f-ceea-467a-9575-1f0a2f8a1c11", title="", source={"channel": "panel", "key": "u"}, conversation_ids=["c"], created_at="2026-01-01T00:00:00+00:00",
        last_activity="2026-01-01T00:00:00+00:00", closed_at=None,
        settings=SessionSettings("haiku", "low", False, True, True),
        claude=ClaudeSession("54476395-c998-4b98-9deb-e00441e3d393"))
    info = render_app_info(AppInfoContext(docs="# Docs\n", settings=settings, token={"configured": True},
                                          memory_used=0, session=session, session_tools=[]))
    assert "This session:" in info and "- Context:" not in info
