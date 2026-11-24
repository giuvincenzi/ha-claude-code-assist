from datetime import timedelta

import pytest

from ha_cca.app_info import AppInfoContext, render_app_info
from ha_cca.config import parse_options
from ha_cca.prompt import CONTEXT_TAG, DEFAULTS, SECTIONS, build_system_prompt, split_context, with_context
from ha_cca.sessions import ClaudeSession, SessionRecord, SessionSettings


def prompt(channel="panel", memory=None, **sections):
    return build_system_prompt(channel, {**DEFAULTS[channel], **sections}, memory)


def test_prompt_with_memory():
    text = prompt(memory="- [1] The study is Office")
    assert "This conversation comes from: the chat in the HA Claude Code Assist panel." in text
    assert "<memory>" in text and "- [1] The study is Office" in text


def test_prompt_without_memory():
    text = prompt()
    assert "<memory" not in text and "ha_cca_memory_add" not in text


def test_prompt_is_stable():
    assert prompt(memory="(no entries)") == prompt(memory="(no entries)")


def test_prompt_is_made_of_the_sections_in_order_with_the_system_rules():
    text = prompt(identity="You are Jarvis.", acting="- Act.", memory="(no entries)")
    tags = ["identity", "personality", "capabilities", "system", "conversation", "response_style", "acting",
            "memory", "memory_entries"]
    assert [text.index(f"<{tag}>") for tag in tags] == sorted(text.index(f"<{tag}>") for tag in tags)
    assert "<identity>\nYou are Jarvis.\n</identity>" in text and "<acting>\n- Act.\n</acting>" in text
    assert "call ha_cca_app_info" in text and "Read the real state with your tools" in text


def test_each_channel_has_its_own_response_style_and_conversation():
    panel, home_assistant = prompt("panel"), prompt("home_assistant")
    assert "The panel renders markdown" in panel and "text-to-speech" not in panel
    assert "text-to-speech" in home_assistant and "The panel renders markdown" not in home_assistant
    assert "This conversation comes from: Home Assistant's Assist" in home_assistant


def test_only_home_assistant_is_told_about_its_context():
    assert f"<{CONTEXT_TAG}>" in prompt("home_assistant")
    assert CONTEXT_TAG not in prompt("panel")


def test_the_system_rules_are_not_in_the_sections_the_user_rewrites():
    for sections in DEFAULTS.values():
        assert sections.keys() == set(SECTIONS)
        assert not any("ha_cca_app_info" in text or "Read the real state" in text for text in sections.values())


def test_a_message_with_context_and_back():
    message = with_context("yes", "  The user was asked whether to close the garage.\n")
    assert message == (f"<{CONTEXT_TAG}>\nThe user was asked whether to close the garage.\n</{CONTEXT_TAG}>\n\nyes")
    assert split_context(message) == ("yes", "The user was asked whether to close the garage.")


@pytest.mark.parametrize("context", [None, "", "  \n"])
def test_a_message_without_context_is_the_text(context):
    assert with_context("hello", context) == "hello"
    assert split_context("hello") == ("hello", None)


def test_only_a_context_at_the_start_counts():
    text = f"what does <{CONTEXT_TAG}>\nx\n</{CONTEXT_TAG}>\n\nmean?"
    assert split_context(text) == (text, None)


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
