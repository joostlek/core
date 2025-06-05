"""KEF tests configuration."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.kef.const import (
    CONF_INVERSE_SPEAKER_MODE,
    CONF_MAX_VOLUME,
    CONF_SUPPORTS_ON,
    CONF_VOLUME_STEP,
    DEFAULT_INVERSE_SPEAKER_MODE,
    DEFAULT_MAX_VOLUME,
    DEFAULT_SUPPORTS_ON,
    DEFAULT_VOLUME_STEP,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TYPE

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.kef.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_kef_client() -> Generator[AsyncMock]:
    """Mock a KEF client."""
    with (
        patch(
            "homeassistant.components.kef.AsyncKefSpeaker",
            autospec=True,
        ) as mock_client,
        patch(
            "homeassistant.components.kef.config_flow.AsyncKefSpeaker",
            new=mock_client,
        ),
    ):
        client = mock_client.return_value
        client.is_online.return_value = True
        yield client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Speaker",
        data={CONF_HOST: "10.0.0.131", CONF_PORT: 5001, CONF_TYPE: "LSX"},
        options={
            CONF_MAX_VOLUME: DEFAULT_MAX_VOLUME,
            CONF_VOLUME_STEP: DEFAULT_VOLUME_STEP,
            CONF_SUPPORTS_ON: DEFAULT_SUPPORTS_ON,
            CONF_INVERSE_SPEAKER_MODE: DEFAULT_INVERSE_SPEAKER_MODE,
        },
    )
