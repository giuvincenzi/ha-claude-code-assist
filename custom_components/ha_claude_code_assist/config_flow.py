"""Sets up HA Claude Code Assist from Supervisor discovery only.

The app announces its address and token at every start, and the token is shown nowhere: a form
asking for it could not be filled in. A new token (the app installed again) reaches an entry
already set up through the next announcement, which updates and reloads it. Home Assistant
offers an ignored or removed discovery again by itself.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .api import AppClient, CannotConnect, InvalidToken
from .const import DOMAIN


class ClaudeCodeAssistConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}
        self._app_name = ""

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> ConfigFlowResult:
        """The app announced itself: its address and token come with it."""
        config = discovery_info.config
        data = {CONF_HOST: config[CONF_HOST], CONF_PORT: int(config[CONF_PORT]), CONF_TOKEN: config[CONF_TOKEN]}
        await self.async_set_unique_id(data[CONF_HOST])
        self._abort_if_unique_id_configured(updates=data)
        self._discovered = data
        self._app_name = discovery_info.name
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = self._discovered
            client = AppClient(async_get_clientsession(self.hass), data[CONF_HOST], data[CONF_PORT], data[CONF_TOKEN])
            try:
                await client.check()
            except InvalidToken:
                errors["base"] = "invalid_token"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=self._app_name or "HA Claude Code Assist", data=data)
        return self.async_show_form(step_id="hassio_confirm", errors=errors,
                                    description_placeholders={"app": self._app_name})

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Added from the list of integrations: it can only come from the app's discovery."""
        return self.async_abort(reason="discovery_only")
