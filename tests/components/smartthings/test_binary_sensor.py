"""Test for the SmartThings binary_sensor platform."""

from unittest.mock import AsyncMock

from pysmartthings import Attribute, Capability
import pytest
from syrupy import SnapshotAssertion

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.smartthings import DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from . import setup_integration, snapshot_smartthings_entities, trigger_update

from tests.common import MockConfigEntry


async def test_all_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    await setup_integration(hass, mock_config_entry)

    snapshot_smartthings_entities(
        hass, entity_registry, snapshot, Platform.BINARY_SENSOR
    )


@pytest.mark.parametrize("device_fixture", ["da_ref_normal_000001"])
async def test_state_update(
    hass: HomeAssistant,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test state update."""
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("binary_sensor.refrigerator_door").state == STATE_OFF

    await trigger_update(
        hass,
        devices,
        "7db87911-7dce-1cf2-7119-b953432a2f09",
        Capability.CONTACT_SENSOR,
        Attribute.CONTACT,
        "open",
    )

    assert hass.states.get("binary_sensor.refrigerator_door").state == STATE_ON


@pytest.mark.parametrize("device_fixture", ["virtual_valve"])
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_deprecated_entity(
    hass: HomeAssistant,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    issue_registry: ir.IssueRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test state update."""
    entity_registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        DOMAIN,
        "612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3.valve",
        suggested_object_id="volvo_valve",
    )
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("binary_sensor.volvo_valve").state == STATE_OFF
    assert issue_registry.async_get_issue(
        DOMAIN, "deprecated_entity_612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3.valve"
    )
