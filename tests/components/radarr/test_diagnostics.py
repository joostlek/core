"""Tests for the diagnostics data provided by the Radarr integration."""
from syrupy import SnapshotAssertion

from homeassistant.components.radarr.const import DOMAIN
from homeassistant.core import HomeAssistant

from . import setup_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    entity_registry_enabled_by_default: None,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    await setup_integration(hass, aioclient_mock)
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    assert await get_diagnostics_for_config_entry(hass, hass_client, entry) == snapshot
