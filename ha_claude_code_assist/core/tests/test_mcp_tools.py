import re

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from ha_cca.mcp_tools import build_mcp_server
from ha_cca.memory import MemoryStore


@pytest.fixture
def setup(tmp_path):
    state = {"memory_enabled": True}
    store = MemoryStore(tmp_path / "memory", max_entries=1, max_entry_length=20)
    server = build_mcp_server(
        memory=lambda: store,
        memory_enabled=lambda: state["memory_enabled"],
        app_info=lambda session_id: f"info for {session_id}",
    )
    return server, store, state


def text(result):
    return " ".join(getattr(block, "text", "") for block in result.content)


async def test_memory_add_and_full_memory_error_is_explained(setup):
    server, _, _ = setup
    assert "Saved as memory entry 1" in text(await server.call_tool("ha_cca_memory_add", {"text": "First fact"}))
    with pytest.raises(ToolError, match=r"The memory is full with 1 entry\. Remove an entry first, in the Memory tab"):
        await server.call_tool("ha_cca_memory_add", {"text": "Second fact"})


async def test_too_long_entry_error_is_explained(setup):
    server, _, _ = setup
    with pytest.raises(ToolError, match="the limit is 20"):
        await server.call_tool("ha_cca_memory_add", {"text": "x" * 21})


async def test_remove_unknown_entry_error_is_explained(setup):
    server, _, _ = setup
    with pytest.raises(ToolError, match="no memory entry with id 7.*ha_cca_memory_list"):
        await server.call_tool("ha_cca_memory_remove", {"entry_id": 7})


async def test_memory_disabled(setup):
    server, _, state = setup
    state["memory_enabled"] = False
    with pytest.raises(ToolError, match="turned off"):
        await server.call_tool("ha_cca_memory_list", {})


async def test_datetime(setup, monkeypatch):
    server, _, _ = setup
    monkeypatch.setenv("TZ", "Europe/Rome")
    answer = text(await server.call_tool("ha_cca_datetime", {}))
    assert re.match(r"\w+day \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}, time zone CE", answer)


async def test_datetime_in_another_time_zone(setup, monkeypatch):
    server, _, _ = setup
    monkeypatch.setenv("TZ", "Europe/Rome")
    answer = text(await server.call_tool("ha_cca_datetime", {"time_zone": "Asia/Tokyo"}))
    assert answer.endswith("time zone Asia/Tokyo (UTC+0900)")


async def test_datetime_unknown_time_zone(setup):
    server, _, _ = setup
    with pytest.raises(ToolError, match="Unknown time zone 'Mars/Base'.*IANA"):
        await server.call_tool("ha_cca_datetime", {"time_zone": "Mars/Base"})


async def test_app_info_without_session(setup):
    server, _, _ = setup
    assert text(await server.call_tool("ha_cca_app_info", {})) == "info for None"
