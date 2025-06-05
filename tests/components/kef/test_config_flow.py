"""Tests for the KEF config flow."""

from unittest.mock import AsyncMock

import pytest

from homeassistant.components.kef.const import (
    CONF_MAX_VOLUME,
    CONF_VOLUME_STEP,
    DEFAULT_INVERSE_SPEAKER_MODE,
    DEFAULT_MAX_VOLUME,
    DEFAULT_SUPPORTS_ON,
    DEFAULT_VOLUME_STEP,
    DOMAIN,
)
from homeassistant.components.kef.media_player import (
    CONF_INVERSE_SPEAKER_MODE,
    CONF_SUPPORTS_ON,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_flow(
    hass: HomeAssistant,
    mock_kef_client: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test full flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131", CONF_TYPE: "LSX", CONF_PORT: 5001},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "10.0.0.131"
    assert result["data"] == {
        CONF_HOST: "10.0.0.131",
        CONF_TYPE: "LSX",
        CONF_PORT: 5001,
    }
    assert result["options"] == {
        CONF_MAX_VOLUME: DEFAULT_MAX_VOLUME,
        CONF_VOLUME_STEP: DEFAULT_VOLUME_STEP,
        CONF_SUPPORTS_ON: DEFAULT_SUPPORTS_ON,
        CONF_INVERSE_SPEAKER_MODE: DEFAULT_INVERSE_SPEAKER_MODE,
    }
    assert not result["result"].unique_id


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (ConnectionError, "cannot_connect"),
        (TimeoutError, "cannot_connect"),
    ],
)
async def test_flow_errors(
    hass: HomeAssistant,
    mock_kef_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test flow errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    mock_kef_client.is_online.side_effect = exception

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131", CONF_TYPE: "LSX", CONF_PORT: 5001},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": error}

    mock_kef_client.is_online.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131", CONF_TYPE: "LSX", CONF_PORT: 5001},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_flow_duplicate_entry(
    hass: HomeAssistant,
    mock_kef_client: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting up a duplicate entry."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "10.0.0.131", CONF_TYPE: "LSX", CONF_PORT: 5001},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
