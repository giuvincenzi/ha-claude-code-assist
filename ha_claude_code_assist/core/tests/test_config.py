import json

import pytest

from ha_cca import config
from ha_cca.config import (
    PROMPT_OPTIONS,
    SettingsError,
    SettingsStore,
    normalize_prompt,
    parse_mcp_servers,
    parse_options,
)
from ha_cca.prompt import DEFAULTS, SECTIONS


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


# --- the prompts (Settings > Agent) --------------------------------------------------


def test_every_section_starts_from_its_default():
    assert parse_options({}).prompts == DEFAULTS
    assert set(PROMPT_OPTIONS) == {f"prompt_{c}_{s}" for c in ("panel", "home_assistant") for s in SECTIONS}


@pytest.mark.parametrize("value", ["", "   ", "\n\t \n", None])
def test_a_blank_section_is_its_default(value):
    assert parse_options({"prompt_panel_identity": value}).prompts["panel"]["identity"] == DEFAULTS["panel"]["identity"]


def test_a_section_the_user_wrote_is_used_without_the_blanks_around_it():
    settings = parse_options({"prompt_home_assistant_personality": "\n  Be brief.  \n"})
    assert settings.prompts["home_assistant"]["personality"] == "Be brief."
    assert settings.prompts["panel"]["personality"] == DEFAULTS["panel"]["personality"]


@pytest.mark.parametrize("value, saved", [
    ("  My own text.\n", "My own text."),
    ("   ", ""),
    (DEFAULTS["panel"]["acting"], ""),  # the default is saved as nothing, so a newer default reaches it
    (f"\n{DEFAULTS['panel']['acting']}  \n", ""),
])
def test_what_is_saved_for_a_section(value, saved):
    assert normalize_prompt("prompt_panel_acting", value) == saved


def test_a_section_must_be_text():
    with pytest.raises(SettingsError) as err:
        parse_options({"prompt_panel_acting": 5})
    assert str(err.value) == "The Acting section of the Chat panel prompt must be text."


async def test_the_store_saves_sections_without_blanks_and_defaults(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr(config, "_supervisor_set_options", saved.append)
    (tmp_path / "options.json").write_text(json.dumps({"model": "haiku"}))
    store = SettingsStore(tmp_path / "options.json", tmp_path / "token.json")
    await store.update({"prompt_panel_identity": " You are Jarvis. ",
                        "prompt_panel_acting": DEFAULTS["panel"]["acting"] + "\n"})
    assert saved[-1]["prompt_panel_identity"] == "You are Jarvis." and saved[-1]["prompt_panel_acting"] == ""
    assert store.settings.prompts["panel"]["identity"] == "You are Jarvis."
    assert store.settings.prompts["panel"]["acting"] == DEFAULTS["panel"]["acting"]
