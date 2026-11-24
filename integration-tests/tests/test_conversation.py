"""The Assist agent: what it sends to the app, and how the app's answer becomes Assist's."""

import json
from pathlib import Path

import pytest
from homeassistant.components import conversation
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import intent
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components import ha_claude_code_assist as integration
from custom_components.ha_claude_code_assist.const import APP_OUTDATED_ISSUE, DOMAIN

HOST = "local-ha-claude-code-assist"
ASSIST = f"http://{HOST}:8099/api/assist"
CHECK = f"{ASSIST}/check"
# This integration's version, as the release writes it in its manifest.
VERSION = json.loads((Path(integration.__file__).parent / "manifest.json").read_text())["version"]
APP = {"X-HA-CCA-App-Version": VERSION}  # an app of the same release


def stream(*items) -> str:
    return "".join(json.dumps(item) + "\n" for item in items)


@pytest.fixture
async def agent(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> MockConfigEntry:
    assert await async_setup_component(hass, "conversation", {})
    aioclient_mock.get(CHECK, json={"ok": True}, headers=APP)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HOST, data={CONF_HOST: HOST, CONF_PORT: 8099, CONF_TOKEN: "secret"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def entity_id(hass: HomeAssistant) -> str:
    """Our agent's entity (Home Assistant has its own agent too)."""
    (entry,) = hass.config_entries.async_entries(DOMAIN)
    (entity,) = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    return entity.entity_id


def sent(aioclient_mock: AiohttpClientMocker) -> dict:
    """The body of the last message sent to the app."""
    _, _, data, headers = [call for call in aioclient_mock.mock_calls if str(call[1]) == ASSIST][-1]
    assert headers["Authorization"] == "Bearer secret"
    assert headers["X-HA-CCA-Integration-Version"] == VERSION
    return data


def app_outdated_issue(hass: HomeAssistant) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, APP_OUTDATED_ISSUE)


async def converse(hass, text, **kwargs) -> conversation.ConversationResult:
    return await conversation.async_converse(hass, text, None, kwargs.pop("context", Context()),
                                             agent_id=entity_id(hass), **kwargs)


async def test_the_answer_streamed_by_the_app_is_the_answer(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, text=stream({"delta": "The kitchen "}, {"delta": "light is on."},
                                            {"done": True, "error": None, "text": ""}))
    result = await converse(hass, "turn on the kitchen light", language="en")
    assert result.response.speech["plain"]["speech"] == "The kitchen light is on."
    body = sent(aioclient_mock)
    assert body["conversation_id"] == result.conversation_id
    assert body["source"] == {"key": "assist", "name": None}


async def test_everything_home_assistant_gave_the_agent_is_sent_as_it_came(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, text=stream({"done": True, "error": None, "text": "Closed."}))
    context = Context()
    await converse(hass, "yes", language="it", context=context,
                   extra_system_prompt="The user was asked whether to close the garage door.")
    ha_input = sent(aioclient_mock)["input"]
    assert ha_input == {
        "text": "yes", "context": context.as_dict(), "conversation_id": None, "device_id": None,
        "satellite_id": None, "language": "it", "agent_id": entity_id(hass),
        "extra_system_prompt": "The user was asked whether to close the garage door.",
    }


async def test_an_answer_that_comes_whole(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, text=stream({"done": True, "error": None, "text": "Done."}))
    result = await converse(hass, "hi")
    assert result.response.speech["plain"]["speech"] == "Done."


async def test_what_went_wrong_in_the_app_is_said(hass, agent, aioclient_mock):
    message = "Claude Code could not sign in because the setup token was rejected."
    aioclient_mock.post(ASSIST, text=stream({"done": True, "error": "authentication_failed", "text": message}))
    result = await converse(hass, "hi")
    assert result.response.speech["plain"]["speech"] == message


async def test_the_same_conversation_keeps_its_id(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, text=stream({"delta": "ok"}, {"done": True, "error": None, "text": ""}))
    first = await converse(hass, "hi")
    second = await conversation.async_converse(hass, "again", first.conversation_id, Context(), agent_id=entity_id(hass))
    assert second.conversation_id == first.conversation_id
    assert sent(aioclient_mock)["conversation_id"] == first.conversation_id


async def test_a_voice_device_is_the_source(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, text=stream({"done": True, "error": None, "text": "ok"}))
    device = dr.async_get(hass).async_get_or_create(config_entry_id=agent.entry_id, identifiers={("test", "kitchen")},
                                                    name="Kitchen speaker")
    await converse(hass, "hi", device_id=device.id)
    assert sent(aioclient_mock)["source"] == {"key": f"device:{device.id}", "name": "Kitchen speaker"}


async def test_a_user_is_the_source_when_no_device_is(hass, agent, aioclient_mock, hass_admin_user):
    aioclient_mock.post(ASSIST, text=stream({"done": True, "error": None, "text": "ok"}))
    await converse(hass, "hi", context=Context(user_id=hass_admin_user.id))
    assert sent(aioclient_mock)["source"] == {"key": f"user:{hass_admin_user.id}", "name": hass_admin_user.name}


async def test_an_app_that_does_not_answer(hass, agent, aioclient_mock):
    # Home Assistant turns the agent's error into Assist's error answer, said to the user.
    aioclient_mock.post(ASSIST, exc=TimeoutError)
    result = await converse(hass, "hi")
    assert result.response.response_type is intent.IntentResponseType.ERROR
    assert result.response.speech["plain"]["speech"] == "HA Claude Code Assist does not answer. Check that the app is running."


async def test_a_refused_token_says_what_to_do(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, status=401)
    result = await converse(hass, "hi")
    assert result.response.response_type is intent.IntentResponseType.ERROR
    assert result.response.speech["plain"]["speech"] == (
        "HA Claude Code Assist refused the token. Restart the app so Home Assistant gets the new one.")


async def test_a_voice_satellite_is_the_source_before_its_device(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, text=stream({"done": True, "error": None, "text": "ok"}))
    hass.states.async_set("assist_satellite.kitchen", "idle", {"friendly_name": "Kitchen satellite"})
    device = dr.async_get(hass).async_get_or_create(config_entry_id=agent.entry_id, identifiers={("test", "sat")},
                                                    name="Satellite device")
    await converse(hass, "hi", satellite_id="assist_satellite.kitchen", device_id=device.id)
    assert sent(aioclient_mock)["source"] == {"key": "satellite:assist_satellite.kitchen", "name": "Kitchen satellite"}


# --- the versions of the app and of this integration --------------------------------


async def test_an_app_of_the_same_release_raises_no_issue(hass, agent, aioclient_mock):
    assert app_outdated_issue(hass) is None


@pytest.mark.parametrize("app_headers", [{}, {"X-HA-CCA-App-Version": "0.0.1"}])
async def test_an_older_app_is_reported_in_repairs_until_it_is_updated(hass, aioclient_mock, app_headers):
    # An app before 0.3.0 reports no version.
    assert await async_setup_component(hass, "conversation", {})
    aioclient_mock.get(CHECK, json={"ok": True}, headers=app_headers)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HOST, data={CONF_HOST: HOST, CONF_PORT: 8099, CONF_TOKEN: "secret"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    issue = app_outdated_issue(hass)
    assert issue is not None and issue.severity is ir.IssueSeverity.WARNING and not issue.is_fixable

    aioclient_mock.post(ASSIST, text=stream({"done": True, "error": None, "text": "ok"}), headers=APP)
    await converse(hass, "hi")  # the app was updated meanwhile
    assert app_outdated_issue(hass) is None


async def test_an_older_app_that_cannot_take_the_message_says_to_update_it(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, status=400, json={"error": "A message needs its text and its source."})
    result = await converse(hass, "hi")
    assert result.response.response_type is intent.IntentResponseType.ERROR
    assert result.response.speech["plain"]["speech"] == (
        "The HA Claude Code Assist app is older than its integration. Update the app in Settings > Apps.")
    assert app_outdated_issue(hass) is not None


async def test_what_the_app_says_when_it_cannot_take_the_message(hass, agent, aioclient_mock):
    message = ("The HA Claude Code Assist integration, version 0.1.0, is older than the app, version 9.0.0. "
               "Update the integration in the Marketplace or HACS, then restart Home Assistant.")
    aioclient_mock.post(ASSIST, status=400, json={"error": message}, headers={"X-HA-CCA-App-Version": "9.0.0"})
    result = await converse(hass, "hi")
    assert result.response.speech["plain"]["speech"] == message
    assert app_outdated_issue(hass) is None


async def test_the_issue_goes_when_the_integration_is_removed(hass, aioclient_mock):
    assert await async_setup_component(hass, "conversation", {})
    aioclient_mock.get(CHECK, json={"ok": True})
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HOST, data={CONF_HOST: HOST, CONF_PORT: 8099, CONF_TOKEN: "secret"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert app_outdated_issue(hass) is not None
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert app_outdated_issue(hass) is None
