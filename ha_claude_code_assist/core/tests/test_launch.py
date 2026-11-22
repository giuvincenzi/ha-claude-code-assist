import json
from pathlib import Path

import pytest

from ha_cca.config import parse_options
from ha_cca.launch import build_launch_spec, builtin_tools
from ha_cca.sessions import ClaudeSession, SessionRecord, SessionSettings

OURS = "8f14e45f-ceea-467a-9575-1f0a2f8a1c11"
CLAUDES = "337ccddc-edb0-464d-9e76-5effee12e96e"
WORKDIR = Path(f"/data/sessions/{OURS}/workdir")


def record(*, web_search=False, read_files=True, memory_enabled=True, claude_id=None) -> SessionRecord:
    return SessionRecord(
        session_id=OURS, title="", source={"channel": "panel", "key": "u"}, conversation_ids=["c"],
        created_at="2026-01-01T00:00:00+00:00", last_activity="2026-01-01T00:00:00+00:00", closed_at=None,
        settings=SessionSettings("haiku", "low", web_search, memory_enabled, read_files),
        claude=ClaudeSession(session_id=claude_id))


def spec(rec: SessionRecord, resume=False):
    settings = parse_options({"mcp_servers": '{"mcpServers": {"ha-mcp": {"type": "http", "url": "http://x"}}}'})
    return build_launch_spec(rec, resume, settings=settings, memory_text="(no entries)",
                             internal_mcp_url="http://127.0.0.1:8099/mcp", workdir=WORKDIR,
                             config_dir=Path("/data/claude"))


def option(command: list[str], name: str) -> str:
    return command[command.index(name) + 1]


@pytest.mark.parametrize("web_search, read_files, tools", [
    (False, False, []),
    (False, True, ["Read"]),
    (True, False, ["WebSearch", "WebFetch"]),
    (True, True, ["Read", "WebSearch", "WebFetch"]),
])
def test_builtin_tools_follow_the_settings(web_search, read_files, tools):
    assert builtin_tools(web_search, read_files) == tools
    command = spec(record(web_search=web_search, read_files=read_files)).command()
    assert option(command, "--tools") == ",".join(tools)


@pytest.mark.parametrize("web_search", [False, True])
def test_read_is_never_an_allowed_tool(web_search):
    # An allow rule for Read would let it read anywhere: it may read only what Claude Code
    # itself lets it read (the session's working directory and the session's own files).
    command = spec(record(web_search=web_search, read_files=True)).command()
    allowed = option(command, "--allowedTools").split(",")
    assert not any(tool == "Read" or tool.startswith("Read(") for tool in allowed)
    assert ("WebFetch" in allowed) is web_search


def test_reads_outside_the_working_directory_are_blocked():
    command = spec(record()).command()
    assert json.loads(option(command, "--settings"))["permissions"] == {"blockReadsOutsideWorkingDirectories": True}
    assert option(command, "--permission-mode") == "dontAsk"


def test_claude_codes_cleanup_comes_a_day_after_ours():
    command = spec(record()).command()  # the default retention: 30 days
    assert json.loads(option(command, "--settings"))["cleanupPeriodDays"] == 31


def test_the_process_starts_in_the_sessions_own_working_directory():
    assert spec(record()).workdir == WORKDIR


def test_a_new_conversation_gets_our_session_id():
    command = spec(record()).command()
    assert option(command, "--session-id") == OURS and "--resume" not in command


def test_resuming_uses_claudes_session_id():
    command = spec(record(claude_id=CLAUDES), resume=True).command()
    assert option(command, "--resume") == CLAUDES and "--session-id" not in command


def test_resuming_needs_claudes_session_id():
    with pytest.raises(ValueError, match="never reported"):
        spec(record(claude_id=None), resume=True)


def test_the_internal_server_knows_our_session_id():
    internal = spec(record(claude_id=CLAUDES), resume=True).mcp_config["mcpServers"]["ha_cca"]
    assert internal["headers"] == {"X-HA-CCA-Session": OURS}


def test_memory_tools_are_removed_when_memory_is_off():
    assert spec(record(memory_enabled=False)).disallowed_tools
    assert spec(record(memory_enabled=True)).disallowed_tools == []
