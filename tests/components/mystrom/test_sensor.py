"""Test the myStrom init."""


from homeassistant.core import HomeAssistant

from .test_init import init_integration

from tests.common import MockConfigEntry


async def test_sensors(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Test the initialization of a myStrom bulb."""
    await init_integration(hass, config_entry, 106)
    state = hass.states.get("sensor.mystrom_device_power")
    assert state.state == "1.69"
    state = hass.states.get("sensor.mystrom_device_temperature")
    assert state.state == "24.87"
