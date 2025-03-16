"""Support for binary sensors through the SmartThings cloud API."""

from __future__ import annotations

from dataclasses import dataclass

from pysmartthings import Attribute, Capability, SmartThings

from homeassistant.components.automation import automations_with_entity
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.script import scripts_with_entity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from . import FullDevice, SmartThingsConfigEntry
from .const import DOMAIN, MAIN
from .entity import SmartThingsEntity


@dataclass(frozen=True, kw_only=True)
class SmartThingsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a SmartThings binary sensor entity."""

    is_on_key: str


CAPABILITY_TO_SENSORS: dict[
    Capability, dict[Attribute, SmartThingsBinarySensorEntityDescription]
] = {
    Capability.ACCELERATION_SENSOR: {
        Attribute.ACCELERATION: SmartThingsBinarySensorEntityDescription(
            key=Attribute.ACCELERATION,
            translation_key="acceleration",
            device_class=BinarySensorDeviceClass.MOVING,
            is_on_key="active",
        )
    },
    Capability.CONTACT_SENSOR: {
        Attribute.CONTACT: SmartThingsBinarySensorEntityDescription(
            key=Attribute.CONTACT,
            device_class=BinarySensorDeviceClass.DOOR,
            is_on_key="open",
        )
    },
    Capability.FILTER_STATUS: {
        Attribute.FILTER_STATUS: SmartThingsBinarySensorEntityDescription(
            key=Attribute.FILTER_STATUS,
            translation_key="filter_status",
            device_class=BinarySensorDeviceClass.PROBLEM,
            is_on_key="replace",
        )
    },
    Capability.MOTION_SENSOR: {
        Attribute.MOTION: SmartThingsBinarySensorEntityDescription(
            key=Attribute.MOTION,
            device_class=BinarySensorDeviceClass.MOTION,
            is_on_key="active",
        )
    },
    Capability.PRESENCE_SENSOR: {
        Attribute.PRESENCE: SmartThingsBinarySensorEntityDescription(
            key=Attribute.PRESENCE,
            device_class=BinarySensorDeviceClass.PRESENCE,
            is_on_key="present",
        )
    },
    Capability.SOUND_SENSOR: {
        Attribute.SOUND: SmartThingsBinarySensorEntityDescription(
            key=Attribute.SOUND,
            device_class=BinarySensorDeviceClass.SOUND,
            is_on_key="detected",
        )
    },
    Capability.TAMPER_ALERT: {
        Attribute.TAMPER: SmartThingsBinarySensorEntityDescription(
            key=Attribute.TAMPER,
            device_class=BinarySensorDeviceClass.TAMPER,
            is_on_key="detected",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
    },
    Capability.VALVE: {
        Attribute.VALVE: SmartThingsBinarySensorEntityDescription(
            key=Attribute.VALVE,
            translation_key="valve",
            device_class=BinarySensorDeviceClass.OPENING,
            is_on_key="open",
            entity_registry_enabled_default=False,
        )
    },
    Capability.WATER_SENSOR: {
        Attribute.WATER: SmartThingsBinarySensorEntityDescription(
            key=Attribute.WATER,
            device_class=BinarySensorDeviceClass.MOISTURE,
            is_on_key="wet",
        )
    },
}


def entity_used_in(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Get list of related automations and scripts."""
    used_in = automations_with_entity(hass, entity_id)
    used_in += scripts_with_entity(hass, entity_id)
    return used_in


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartThingsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add binary sensors for a config entry."""
    entry_data = entry.runtime_data
    entity_registry = er.async_get(hass)
    entities: list[SmartThingsBinarySensor] = []

    def add_deprecated_entity(
        dev: FullDevice,
        desc: SmartThingsBinarySensorEntityDescription,
        cap: Capability,
        attr: Attribute,
    ) -> None:
        """Add deprecated entities."""
        entity_uid = f"{dev.device.device_id}.{attr}"
        if entity_id := entity_registry.async_get_entity_id(
            BINARY_SENSOR_DOMAIN, DOMAIN, entity_uid
        ):
            entity_entry = entity_registry.async_get(entity_id)
            if entity_entry and entity_entry.disabled:
                entity_registry.async_remove(entity_id)
                async_delete_issue(
                    hass,
                    DOMAIN,
                    f"deprecated_entity_{entity_uid}",
                )
            elif entity_entry:
                entities.append(
                    SmartThingsBinarySensor(
                        entry_data.client,
                        dev,
                        desc,
                        entry_data.rooms,
                        cap,
                        attr,
                    )
                )
                if entity_used_in(hass, entity_id):
                    async_create_issue(
                        hass,
                        DOMAIN,
                        f"deprecated_entity_{entity_uid}",
                        breaks_in_ha_version="2025.10.0",
                        is_fixable=False,
                        severity=IssueSeverity.WARNING,
                        translation_key="deprecated_entity",
                        translation_placeholders={
                            "name": str(
                                entity_entry.name or entity_entry.original_name
                            ),
                            "entity": entity_id,
                        },
                    )

    for device in entry_data.devices.values():
        for capability, attribute_map in CAPABILITY_TO_SENSORS.items():
            if capability in device.status[MAIN]:
                if capability is Capability.VALVE:
                    for attribute, description in attribute_map.items():
                        add_deprecated_entity(
                            device, description, capability, attribute
                        )
                else:
                    entities.extend(
                        SmartThingsBinarySensor(
                            entry_data.client,
                            device,
                            description,
                            entry_data.rooms,
                            capability,
                            attribute,
                        )
                        for attribute, description in attribute_map.items()
                    )
    async_add_entities(entities)


class SmartThingsBinarySensor(SmartThingsEntity, BinarySensorEntity):
    """Define a SmartThings Binary Sensor."""

    entity_description: SmartThingsBinarySensorEntityDescription

    def __init__(
        self,
        client: SmartThings,
        device: FullDevice,
        entity_description: SmartThingsBinarySensorEntityDescription,
        rooms: dict[str, str],
        capability: Capability,
        attribute: Attribute,
    ) -> None:
        """Init the class."""
        super().__init__(client, device, rooms, {capability})
        self._attribute = attribute
        self.capability = capability
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.device.device_id}.{attribute}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return (
            self.get_attribute_value(self.capability, self._attribute)
            == self.entity_description.is_on_key
        )
