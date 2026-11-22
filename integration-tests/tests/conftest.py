"""Every test loads the integration from custom_components/, in a Home Assistant whose base
component is set up, as in a real one (conversation needs it for the entities exposed to Assist)."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
async def base_component(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "homeassistant", {})
