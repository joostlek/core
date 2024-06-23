"""Test the Dio Chacon Cover sensor."""

import logging
from unittest.mock import patch

from dio_chacon_wifi_api import DIOChaconAPIClient
from dio_chacon_wifi_api.const import DeviceTypeEnum

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    CoverDeviceClass,
    CoverEntityFeature,
)
from homeassistant.components.dio_chacon.const import DOMAIN
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    CONF_PASSWORD,
    CONF_UNIQUE_ID,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry

_LOGGER = logging.getLogger(__name__)

MOCK_COVER_DEVICE = {
    "L4HActuator_idmock1": {
        "id": "L4HActuator_idmock1",
        "name": "Shutter mock 1",
        "type": "SHUTTER",
        "model": "CERSwd-3B_1.0.6",
        "connected": True,
        "openlevel": 75,
        "movement": "stop",
    }
}


async def test_cover(hass: HomeAssistant, entity_registry: er.EntityRegistry) -> None:
    """Test the creation and values of the Dio Chacon covers."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test_entry_unique_id",
        data={
            CONF_USERNAME: "dummylogin",
            CONF_PASSWORD: "dummypass",
            CONF_UNIQUE_ID: "dummy-user-id",
        },
    )

    entry.add_to_hass(hass)

    def mock_side_effect(*args, **kwargs):
        if kwargs["device_type_to_search"] == [DeviceTypeEnum.SHUTTER]:
            return MOCK_COVER_DEVICE
        return None

    with patch(
        "dio_chacon_wifi_api.DIOChaconAPIClient.search_all_devices",
        side_effect=mock_side_effect,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity = entity_registry.async_get("cover.shutter_mock_1")
    _LOGGER.debug("Entity cover mock registered : %s", entity)
    assert entity.unique_id == "L4HActuator_idmock1"
    assert entity.entity_id == "cover.shutter_mock_1"

    state = hass.states.get("cover.shutter_mock_1")
    _LOGGER.debug("Entity cover mock state : %s", state.attributes)

    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 75
    assert state.attributes.get(ATTR_DEVICE_CLASS) == CoverDeviceClass.SHUTTER
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Shutter mock 1"
    assert (
        state.attributes.get(ATTR_SUPPORTED_FEATURES)
        == CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.STOP
    )

    with patch(
        "dio_chacon_wifi_api.DIOChaconAPIClient.move_shutter_direction",
    ):
        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: entity.entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()
        state = hass.states.get("cover.shutter_mock_1")
        assert state.state == STATE_CLOSING

        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: entity.entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()
        state = hass.states.get("cover.shutter_mock_1")
        assert state.state == STATE_OPEN

        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: entity.entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()
        state = hass.states.get("cover.shutter_mock_1")
        assert state.state == STATE_OPENING

    with patch(
        "dio_chacon_wifi_api.DIOChaconAPIClient.move_shutter_percentage",
    ):
        await hass.services.async_call(
            COVER_DOMAIN,
            SERVICE_SET_COVER_POSITION,
            {ATTR_POSITION: 25, ATTR_ENTITY_ID: entity.entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()
        state = hass.states.get("cover.shutter_mock_1")
        assert state.state == STATE_OPENING

    # Server side callback tests
    client: DIOChaconAPIClient = entry.runtime_data
    client._callback_device_state(
        {
            "id": "L4HActuator_idmock1",
            "connected": True,
            "openlevel": 79,
            "movement": "stop",
        }
    )
    await hass.async_block_till_done()
    state = hass.states.get("cover.shutter_mock_1")
    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 79
    assert state.state == STATE_OPEN

    client._callback_device_state(
        {
            "id": "L4HActuator_idmock1",
            "connected": True,
            "openlevel": 90,
            "movement": "up",
        }
    )
    await hass.async_block_till_done()
    state = hass.states.get("cover.shutter_mock_1")
    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 90
    assert state.state == STATE_OPENING

    client._callback_device_state(
        {
            "id": "L4HActuator_idmock1",
            "connected": True,
            "openlevel": 60,
            "movement": "down",
        }
    )
    await hass.async_block_till_done()
    state = hass.states.get("cover.shutter_mock_1")
    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 60
    assert state.state == STATE_CLOSING

    # Tests coverage for unload actions.
    with patch(
        "dio_chacon_wifi_api.DIOChaconAPIClient.disconnect",
    ):
        await hass.config_entries.async_unload(entry.entry_id)

    # pytest.fail("Fails to display logs of tests")


async def test_no_cover_found(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test the cover absence."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="test_entry_unique_id",
        data={
            CONF_USERNAME: "dummylogin",
            CONF_PASSWORD: "dummypass",
            CONF_UNIQUE_ID: "dummy-user-id",
        },
    )

    entry.add_to_hass(hass)

    with patch(
        "dio_chacon_wifi_api.DIOChaconAPIClient.search_all_devices",
        return_value=None,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity = entity_registry.async_get("cover.shutter_mock_1")
    _LOGGER.debug("Entity cover mock not found : %s", entity)
    assert not entity
