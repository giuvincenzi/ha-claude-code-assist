"""HA Claude Code Assist: the app's assistant as an Assist conversation agent."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AppClient, CannotConnect, InvalidToken

PLATFORMS = [Platform.CONVERSATION]

type ClaudeCodeAssistConfigEntry = ConfigEntry[AppClient]


async def async_setup_entry(hass: HomeAssistant, entry: ClaudeCodeAssistConfigEntry) -> bool:
    client = AppClient(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT],
                       entry.data[CONF_TOKEN])
    try:
        await client.check()
    except InvalidToken as err:
        # The app was installed again: its next start announces the new token, which reloads
        # this entry (config_flow.py). Until then, Home Assistant retries.
        raise ConfigEntryNotReady(
            "HA Claude Code Assist refused the token. Restart the app so Home Assistant gets the new one.") from err
    except CannotConnect as err:
        raise ConfigEntryNotReady("HA Claude Code Assist does not answer. Check that the app is running.") from err
    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ClaudeCodeAssistConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
