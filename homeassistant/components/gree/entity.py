"""Entity object for shared properties of Gree entities."""
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .bridge import DeviceDataUpdateCoordinator
from .const import DOMAIN


class GreeEntity(CoordinatorEntity[DeviceDataUpdateCoordinator]):
    """Generic Gree entity (base class)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DeviceDataUpdateCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._name = f"{coordinator.device.device_info.name}"
        self._mac = coordinator.device.device_info.mac
        self._attr_unique_id = f"{self._mac}_{key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, self._mac)},
            identifiers={(DOMAIN, self._mac)},
            manufacturer="Gree",
            name=self._name,
        )
