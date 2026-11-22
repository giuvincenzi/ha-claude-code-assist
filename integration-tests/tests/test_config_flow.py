"""Setting up the integration: only by discovery, which also brings a new token; and starting it."""

from homeassistant.config_entries import SOURCE_HASSIO, SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.ha_claude_code_assist.const import DOMAIN

HOST = "local-ha-claude-code-assist"
CHECK = f"http://{HOST}:8099/api/assist/check"
DATA = {CONF_HOST: HOST, CONF_PORT: 8099, CONF_TOKEN: "secret"}
DISCOVERY = HassioServiceInfo(config={"host": HOST, "port": 8099, "token": "secret"}, name="HA Claude Code Assist",
                              slug="local_ha_claude_code_assist", uuid="1234")


async def test_discovery_sets_it_up_after_a_confirmation(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(CHECK, json={"ok": True})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_HASSIO}, data=DISCOVERY)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "hassio_confirm"
    assert result["description_placeholders"] == {"app": "HA Claude Code Assist"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HA Claude Code Assist" and result["data"] == DATA
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == "Bearer secret"


async def test_discovery_of_an_app_that_does_not_answer(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(CHECK, exc=TimeoutError)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_HASSIO}, data=DISCOVERY)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "cannot_connect"}


async def test_discovery_again_takes_over_a_new_token(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HOST, data={**DATA, CONF_TOKEN: "old"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_HASSIO}, data=DISCOVERY)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
    assert entry.data[CONF_TOKEN] == "secret"


async def test_it_cannot_be_added_by_hand(hass: HomeAssistant):
    # The token is shown nowhere: the setup comes only from the app's discovery.
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "discovery_only"


async def test_a_refused_token_waits_for_the_apps_new_one(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    # The app was installed again with a new token: no form, Home Assistant retries, and the app's
    # next announcement brings the new token and sets the integration up again.
    aioclient_mock.get(CHECK, status=401)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HOST, data={**DATA, CONF_TOKEN: "old"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []

    aioclient_mock.clear_requests()
    aioclient_mock.get(CHECK, json={"ok": True})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_HASSIO}, data=DISCOVERY)
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"
    await hass.async_block_till_done()
    assert entry.data == DATA and entry.state is ConfigEntryState.LOADED


async def test_starting_while_the_app_is_stopped_is_retried(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    aioclient_mock.get(CHECK, exc=TimeoutError)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HOST, data=DATA)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
