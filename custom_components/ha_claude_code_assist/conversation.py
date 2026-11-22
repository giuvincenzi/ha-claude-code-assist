"""The Assist conversation agent: every message goes to the app, and its answer streams back so
the speech can start before it is complete."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal

from homeassistant.components import conversation
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ClaudeCodeAssistConfigEntry
from .api import CannotConnect, InvalidToken
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ClaudeCodeAssistConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([ClaudeCodeAssistAgent(entry)])


class ClaudeCodeAssistAgent(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supports_streaming = True
    # It acts on the home through the tools the app gives it.
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, entry: ClaudeCodeAssistConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="HA Claude Code Assist",
                                            entry_type=DeviceEntryType.SERVICE)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    def _source(self, user_input: conversation.ConversationInput) -> tuple[str, str | None]:
        """Who is talking, as the app keys its sessions: the voice device, the device, or the
        user; with a name to show in the panel."""
        if user_input.satellite_id:
            entity = er.async_get(self.hass).async_get(user_input.satellite_id)
            state = self.hass.states.get(user_input.satellite_id)
            name = state.name if state else (entity.name or entity.original_name if entity else None)
            return f"satellite:{user_input.satellite_id}", name
        if user_input.device_id:
            device = dr.async_get(self.hass).async_get(user_input.device_id)
            return f"device:{user_input.device_id}", (device.name_by_user or device.name) if device else None
        if user_input.context.user_id:
            return f"user:{user_input.context.user_id}", None  # the name comes from the user's account
        return "assist", None

    async def _async_handle_message(self, user_input: conversation.ConversationInput,
                                    chat_log: conversation.ChatLog) -> conversation.ConversationResult:
        key, name = self._source(user_input)
        if user_input.context.user_id and name is None:
            user = await self.hass.auth.async_get_user(user_input.context.user_id)
            name = user.name if user else None
        try:
            async for _content in chat_log.async_add_delta_content_stream(
                self.entity_id, self._answer(user_input, chat_log.conversation_id, key, name)
            ):
                pass
        except InvalidToken as err:
            raise HomeAssistantError(
                "HA Claude Code Assist refused the token. Restart the app so Home Assistant gets the new one.") from err
        except CannotConnect as err:
            raise HomeAssistantError("HA Claude Code Assist does not answer. Check that the app is running.") from err
        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    async def _answer(self, user_input: conversation.ConversationInput, conversation_id: str, key: str,
                      name: str | None) -> AsyncIterator[conversation.AssistantContentDeltaDict]:
        yield {"role": "assistant"}
        async for item in self.entry.runtime_data.converse(user_input.text, conversation_id, key, name,
                                                           user_input.language):
            if "delta" in item:
                yield {"content": item["delta"]}
            elif item.get("done") and item.get("text"):
                # The whole answer when nothing streamed, or what went wrong: said as the answer.
                yield {"content": item["text"]}
