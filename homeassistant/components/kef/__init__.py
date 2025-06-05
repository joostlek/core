"""The KEF Wireless Speakers component."""

from __future__ import annotations

from aiokef import AsyncKefSpeaker

from homeassistant.components.kef.const import (
    CONF_INVERSE_SPEAKER_MODE,
    CONF_MAX_VOLUME,
    CONF_STANDBY_TIME,
    CONF_VOLUME_STEP,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
]

type KEFConfigEntry = ConfigEntry[AsyncKefSpeaker]


async def async_setup_entry(hass: HomeAssistant, entry: KEFConfigEntry) -> bool:
    """Set up KEF from a config entry."""

    client = AsyncKefSpeaker(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.options[CONF_VOLUME_STEP],
        entry.options[CONF_MAX_VOLUME],
        entry.options[CONF_STANDBY_TIME],
        entry.options[CONF_INVERSE_SPEAKER_MODE],
        loop=hass.loop,
    )
    if not await client.is_online():
        raise ConfigEntryNotReady

    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: KEFConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
