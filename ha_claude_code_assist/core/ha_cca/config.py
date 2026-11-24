"""App options: read from the Supervisor's options file, updated through the Supervisor API."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from . import supervisor
from .prompt import CHANNELS, DEFAULTS, HOME_ASSISTANT, PANEL, SECTIONS

MODELS = ("haiku", "sonnet", "opus")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
INTERNAL_MCP_SERVER = "ha_cca"
# A token from `claude setup-token` is valid for one year.
TOKEN_VALIDITY = timedelta(days=365)


class SettingsError(ValueError):
    """Invalid option value."""


# How the panel names the options, for error messages.
OPTION_NAMES = {
    "session_timeout_minutes": "The timeout",
    "session_retention_days": "The days to keep sessions",
    "memory_max_entries": "The maximum number of memory entries",
    "memory_max_entry_length": "The maximum length of a memory entry",
    "memory_enabled": "Long-term memory",
    "web_search": "Web search",
    "read_files": "Read files",
}

# How the panel names the channels and the sections of the prompt (Settings > Agent).
CHANNEL_NAMES = {PANEL: "Chat panel", HOME_ASSISTANT: "Home Assistant"}
SECTION_NAMES = {"identity": "Identity", "personality": "Personality", "capabilities": "Capabilities",
                 "response_style": "Response style", "acting": "Acting"}


def prompt_option(channel: str, section: str) -> str:
    """The option that holds a section of a channel's prompt: empty means the default text."""
    return f"prompt_{channel}_{section}"


PROMPT_OPTIONS = {prompt_option(c, s): (c, s) for c in CHANNELS for s in SECTIONS}
OPTION_NAMES.update({key: f"The {SECTION_NAMES[s]} section of the {CHANNEL_NAMES[c]} prompt"
                     for key, (c, s) in PROMPT_OPTIONS.items()})


def _one_of(choices: tuple[str, ...]) -> str:
    return f"{', '.join(choices[:-1])} or {choices[-1]}"


@dataclass(frozen=True)
class Settings:
    oauth_token: str
    model: str
    effort: str
    mcp_servers: dict[str, Any]
    session_timeout: timedelta
    session_retention: timedelta  # sessions with no messages for longer are deleted
    memory_enabled: bool
    memory_max_entries: int
    memory_max_entry_length: int
    web_search: bool
    read_files: bool
    # The text of every section of every channel's prompt: the user's, or the default.
    prompts: dict[str, dict[str, str]]


def normalize_prompt(key: str, value: Any) -> str:
    """What is saved for a section: the text without leading and trailing blanks, or nothing
    when it is blank or the default, so a later version's default reaches it."""
    if not isinstance(value, str):
        raise SettingsError(f"{OPTION_NAMES[key]} must be text.")
    channel, section = PROMPT_OPTIONS[key]
    text = value.strip()
    return "" if text == DEFAULTS[channel][section] else text


def parse_mcp_servers(text: str) -> dict[str, Any]:
    """Parses and validates the user's MCP configuration (Claude Code format)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise SettingsError(f"The MCP servers configuration is not valid JSON. Check line {err.lineno}.") from err
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers"), dict):
        raise SettingsError('The MCP servers configuration must be an object with an "mcpServers" object inside.')
    for name, server in data["mcpServers"].items():
        if name == INTERNAL_MCP_SERVER:
            raise SettingsError(f'The name "{INTERNAL_MCP_SERVER}" is reserved for the app\'s own server. Choose another name.')
        if not isinstance(server, dict):
            raise SettingsError(f'The configuration of the MCP server "{name}" must be an object.')
    return data["mcpServers"]


def parse_options(raw: dict[str, Any]) -> Settings:
    """Builds Settings from the raw options, validating every value."""
    model = raw.get("model", "haiku")
    effort = raw.get("effort", "low")
    if model not in MODELS:
        raise SettingsError(f"The model must be {_one_of(MODELS)}.")
    if effort not in EFFORTS:
        raise SettingsError(f"The effort must be {_one_of(EFFORTS)}.")

    def positive_int(key: str, default: int) -> int:
        value = raw.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise SettingsError(f"{OPTION_NAMES[key]} must be a whole number, 1 or more.")
        return value

    def boolean(key: str, default: bool) -> bool:
        value = raw.get(key, default)
        if not isinstance(value, bool):
            raise SettingsError(f"{OPTION_NAMES[key]} must be on or off.")
        return value

    return Settings(
        oauth_token=raw.get("claude_code_oauth_token") or "",
        model=model,
        effort=effort,
        mcp_servers=parse_mcp_servers(raw.get("mcp_servers") or '{"mcpServers": {}}'),
        session_timeout=timedelta(minutes=positive_int("session_timeout_minutes", 50)),
        session_retention=timedelta(days=positive_int("session_retention_days", 30)),
        memory_enabled=boolean("memory_enabled", True),
        memory_max_entries=positive_int("memory_max_entries", 100),
        memory_max_entry_length=positive_int("memory_max_entry_length", 500),
        web_search=boolean("web_search", False),
        read_files=boolean("read_files", True),
        prompts=_prompts(raw),
    )


def _prompts(raw: dict[str, Any]) -> dict[str, dict[str, str]]:
    prompts: dict[str, dict[str, str]] = {channel: {} for channel in CHANNELS}
    for key, (channel, section) in PROMPT_OPTIONS.items():
        prompts[channel][section] = normalize_prompt(key, raw.get(key) or "") or DEFAULTS[channel][section]
    return prompts


class SettingsStore:
    """Current settings. Changes go through the Supervisor, which validates
    and persists them; the Supervisor rewrites options.json only at the next
    app start, so the store keeps the accepted values in memory."""

    def __init__(self, options_file: Path, token_meta_file: Path) -> None:
        self._token_meta_file = token_meta_file
        self._raw: dict[str, Any] = json.loads(options_file.read_text())
        self.settings = parse_options(self._raw)
        self._token_configured_at = self._track_token(self.settings.oauth_token)

    @property
    def raw(self) -> dict[str, Any]:
        return dict(self._raw)

    def token_status(self) -> dict[str, Any]:
        if not self.settings.oauth_token:
            return {"configured": False}
        configured_at = self._token_configured_at
        return {
            "configured": True,
            "configured_at": configured_at.isoformat(),
            "expires_at": (configured_at + TOKEN_VALIDITY).isoformat(),
        }

    async def update(self, changes: dict[str, Any]) -> Settings:
        changes = {key: normalize_prompt(key, value) if key in PROMPT_OPTIONS else value
                   for key, value in changes.items()}
        raw = {**self._raw, **changes}
        settings = parse_options(raw)  # local validation first, clear errors
        await asyncio.to_thread(_supervisor_set_options, raw)
        self._raw = raw
        self.settings = settings
        self._token_configured_at = self._track_token(settings.oauth_token)
        return settings

    def _track_token(self, token: str) -> datetime:
        """Records when the current token was first seen, to estimate its expiry."""
        fingerprint = hashlib.sha256(token.encode()).hexdigest()[:16] if token else ""
        try:
            meta = json.loads(self._token_meta_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            meta = {}
        if meta.get("fingerprint") != fingerprint:
            meta = {"fingerprint": fingerprint, "configured_at": datetime.now(UTC).isoformat()}
            self._token_meta_file.write_text(json.dumps(meta))
        return datetime.fromisoformat(meta["configured_at"])


def _supervisor_set_options(options: dict[str, Any]) -> None:
    body = supervisor.call("POST", "/addons/self/options", {"options": options})
    if body.get("result") != "ok":
        raise SettingsError(body.get("message") or "Home Assistant did not accept the settings.")
