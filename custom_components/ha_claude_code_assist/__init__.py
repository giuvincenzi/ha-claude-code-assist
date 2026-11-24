"""HA Claude Code Assist: the app's assistant as an Assist conversation agent."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration

from .api import AppClient, CannotConnect, InvalidToken, app_outdated
from .const import APP_OUTDATED_ISSUE, DOMAIN

PLATFORMS = [Platform.CONVERSATION]

type ClaudeCodeAssistConfigEntry = ConfigEntry[AppClient]


async def async_integration_version(hass: HomeAssistant) -> str:
    """This integration's version, from its manifest (written by the release)."""
    return str((await async_get_integration(hass, DOMAIN)).version)


@callback
def _app_version_heard(hass: HomeAssistant, app_version: str | None, version: str) -> None:
    """Raises the Repairs issue while the app is older than this integration, and clears it."""
    if app_outdated(app_version, version):
        ir.async_create_issue(hass, DOMAIN, APP_OUTDATED_ISSUE, is_fixable=False,
                              severity=ir.IssueSeverity.WARNING, translation_key=APP_OUTDATED_ISSUE)
    else:
        ir.async_delete_issue(hass, DOMAIN, APP_OUTDATED_ISSUE)


async def async_setup_entry(hass: HomeAssistant, entry: ClaudeCodeAssistConfigEntry) -> bool:
    version = await async_integration_version(hass)
    client = AppClient(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT],
                       entry.data[CONF_TOKEN], version,
                       on_app_version=lambda app_version: _app_version_heard(hass, app_version, version))
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


async def async_remove_entry(hass: HomeAssistant, entry: ClaudeCodeAssistConfigEntry) -> None:
    ir.async_delete_issue(hass, DOMAIN, APP_OUTDATED_ISSUE)
