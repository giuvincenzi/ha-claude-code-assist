import pytest

from ha_cca.config import SettingsError, parse_mcp_servers, parse_options


def test_defaults():
    settings = parse_options({})
    assert settings.model == "haiku"
    assert settings.effort == "low"
    assert settings.mcp_servers == {}
    assert settings.session_timeout.total_seconds() == 50 * 60
    assert settings.oauth_token == ""
    assert settings.memory_enabled is True
    assert settings.web_search is False
    assert settings.read_files is True
    assert settings.session_retention.days == 30


def test_mcp_servers_parsed():
    servers = parse_mcp_servers('{"mcpServers": {"ha-mcp": {"type": "http", "url": "http://x"}}}')
    assert servers == {"ha-mcp": {"type": "http", "url": "http://x"}}


@pytest.mark.parametrize("text, message", [
    ("{", "not valid JSON"),
    ("[]", '"mcpServers" object'),
    ('{"mcpServers": []}', '"mcpServers" object'),
    ('{"mcpServers": {"ha_cca": {}}}', "reserved"),
    ('{"mcpServers": {"x": 1}}', "must be an object"),
])
def test_mcp_servers_rejected(text, message):
    with pytest.raises(SettingsError, match=message):
        parse_mcp_servers(text)


@pytest.mark.parametrize("raw", [
    {"model": "gpt"},
    {"effort": "extreme"},
    {"session_timeout_minutes": 0},
    {"memory_max_entries": True},
    {"web_search": "yes"},
    {"memory_enabled": 1},
])
def test_invalid_options(raw):
    with pytest.raises(SettingsError):
        parse_options(raw)


@pytest.mark.parametrize("raw, message", [
    ({"model": "gpt"}, "The model must be haiku, sonnet or opus."),
    ({"effort": "extreme"}, "The effort must be low, medium, high, xhigh or max."),
    ({"session_timeout_minutes": 0}, "The timeout must be a whole number, 1 or more."),
    ({"session_retention_days": 0}, "The days to keep sessions must be a whole number, 1 or more."),
    ({"memory_max_entries": True}, "The maximum number of memory entries must be a whole number, 1 or more."),
    ({"memory_max_entry_length": -5}, "The maximum length of a memory entry must be a whole number, 1 or more."),
    ({"web_search": "yes"}, "Web search must be on or off."),
    ({"memory_enabled": 1}, "Long-term memory must be on or off."),
    ({"mcp_servers": "{"}, "The MCP servers configuration is not valid JSON. Check line 1."),
])
def test_errors_use_the_names_the_user_sees(raw, message):
    with pytest.raises(SettingsError) as err:
        parse_options(raw)
    assert str(err.value) == message
