"""Number platform for Zinvolt integration."""

from zinvolt.models import SmartMode

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ZinvoltConfigEntry, ZinvoltDeviceCoordinator
from .entity import ZinvoltEntity

OPTIONS = [mode.lower() for mode in SmartMode if mode != SmartMode.CUSTOM]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZinvoltConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize the entries."""

    async_add_entities(
        ZinvoltSmartModeSelect(coordinator)
        for coordinator in entry.runtime_data.values()
    )


class ZinvoltSmartModeSelect(ZinvoltEntity, SelectEntity):
    """Zinvolt smart mode select."""

    _attr_options = OPTIONS
    _attr_translation_key = "smart_mode"

    def __init__(self, coordinator: ZinvoltDeviceCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.serial_number}.smart_mode"

    @property
    def current_option(self) -> str | None:
        """Return the current smart mode."""
        if (smart_mode := self.coordinator.data.smart_mode) is not SmartMode.CUSTOM:
            return smart_mode.lower()
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the smart mode."""
        await self.coordinator.client.set_smart_mode(
            self.coordinator.battery.identifier, SmartMode(option)
        )
        await self.coordinator.async_request_refresh()
