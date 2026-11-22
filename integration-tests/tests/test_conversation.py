"""The Assist agent: what it sends to the app, and how the app's answer becomes Assist's."""

import json

import pytest
from homeassistant.components import conversation
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import intent
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.ha_claude_code_assist.const import DOMAIN

HOST = "local-ha-claude-code-assist"
ASSIST = f"http://{HOST}:8099/api/assist"
CHECK = f"{ASSIST}/check"


def stream(*items) -> str:
    return "".join(json.dumps(item) + "\n" for item in items)


@pytest.fixture
async def agent(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> MockConfigEntry:
    assert await async_setup_component(hass, "conversation", {})
    aioclient_mock.get(CHECK, json={"ok": True})
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
    return data


async def converse(hass, text, **kwargs) -> conversation.ConversationResult:
    return await conversation.async_converse(hass, text, None, kwargs.pop("context", Context()),
                                             agent_id=entity_id(hass), **kwargs)


async def test_the_answer_streamed_by_the_app_is_the_answer(hass, agent, aioclient_mock):
    aioclient_mock.post(ASSIST, text=stream({"delta": "The kitchen "}, {"delta": "light is on."},
                                            {"done": True, "error": None, "text": ""}))
    result = await converse(hass, "turn on the kitchen light", language="en")
    assert result.response.speech["plain"]["speech"] == "The kitchen light is on."
    body = sent(aioclient_mock)
    assert body["text"] == "turn on the kitchen light" and body["language"] == "en"
    assert body["conversation_id"] == result.conversation_id
    assert body["source"] == {"key": "assist", "name": None}


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
