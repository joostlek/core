"""Update entity for Radarr."""
from __future__ import annotations

from aiopyarr import Update

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RadarrEntity
from .const import DOMAIN

UPDATE_ENTITY = UpdateEntityDescription(key="update", translation_key="update")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up update entity for Radarr component."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["update"]
    async_add_entities([RadarrUpdateEntity(coordinator, UPDATE_ENTITY)])


class RadarrUpdateEntity(RadarrEntity[list[Update]], UpdateEntity):
    """Update entity for Radarr."""

    @property
    def installed_version(self) -> str | None:
        """Version currently in use."""
        for update in self.coordinator.data:
            if update.installed:
                return update.version
        return None

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        if not self.coordinator.data:
            return self.installed_version

        return self.coordinator.data[0].version

    @property
    def supported_features(self) -> UpdateEntityFeature:
        """Flag supported features."""
        if self.latest_version == self.installed_version:
            return UpdateEntityFeature(0)
        return UpdateEntityFeature.RELEASE_NOTES

    def release_notes(self) -> str | None:
        """Return the release notes."""
        notes = ""
        for update in self.coordinator.data:
            if update.installed:
                break
            notes += (
                f"## Version {update.version} - {update.releaseDate.strftime('%D')}\n"
            )
            if len(update.changes.new) > 0:
                notes += "### New:\n"
            for new in update.changes.new:
                notes += f" - {new}\n"
            if len(update.changes.fixed) > 0:
                notes += "### Fixed:\n"
            for fixed in update.changes.fixed:
                notes += f" - {fixed}\n"

        return notes
