"""Diagnostics support for Radarr."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import RadarrDataUpdateCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinators: dict[str, RadarrDataUpdateCoordinator[Any]] = hass.data[DOMAIN][
        entry.entry_id
    ]
    coordinator_data = {
        coordinator_label: coordinator.data
        for coordinator_label, coordinator in coordinators.items()
    }
    return coordinator_data
