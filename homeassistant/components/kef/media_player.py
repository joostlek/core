"""Platform for the KEF Wireless Speakers."""

from __future__ import annotations

from datetime import timedelta
from functools import partial
import ipaddress
import logging

from aiokef import AsyncKefSpeaker
from aiokef.aiokef import DSP_OPTION_MAPPING
from getmac import get_mac_address
import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_TYPE
from homeassistant.core import (
    CALLBACK_TYPE,
    DOMAIN as HOMEASSISTANT_DOMAIN,
    HomeAssistant,
)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import KEFConfigEntry
from .const import (
    CONF_INVERSE_SPEAKER_MODE,
    CONF_MAX_VOLUME,
    CONF_STANDBY_TIME,
    CONF_SUPPORTS_ON,
    CONF_VOLUME_STEP,
    DEFAULT_INVERSE_SPEAKER_MODE,
    DEFAULT_MAX_VOLUME,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SUPPORTS_ON,
    DEFAULT_VOLUME_STEP,
)

_LOGGER = logging.getLogger(__name__)


DOMAIN = "kef"

SCAN_INTERVAL = timedelta(seconds=30)

SOURCES = {"LSX": ["Wifi", "Bluetooth", "Aux", "Opt"]}
SOURCES["LS50"] = SOURCES["LSX"] + ["Usb"]

SERVICE_MODE = "set_mode"
SERVICE_DESK_DB = "set_desk_db"
SERVICE_WALL_DB = "set_wall_db"
SERVICE_TREBLE_DB = "set_treble_db"
SERVICE_HIGH_HZ = "set_high_hz"
SERVICE_LOW_HZ = "set_low_hz"
SERVICE_SUB_DB = "set_sub_db"
SERVICE_UPDATE_DSP = "update_dsp"

DSP_SCAN_INTERVAL = timedelta(seconds=3600)

PLATFORM_SCHEMA = MEDIA_PLAYER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TYPE): vol.In(["LS50", "LSX"]),
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MAX_VOLUME, default=DEFAULT_MAX_VOLUME): cv.small_float,
        vol.Optional(CONF_VOLUME_STEP, default=DEFAULT_VOLUME_STEP): cv.small_float,
        vol.Optional(
            CONF_INVERSE_SPEAKER_MODE, default=DEFAULT_INVERSE_SPEAKER_MODE
        ): cv.boolean,
        vol.Optional(CONF_SUPPORTS_ON, default=DEFAULT_SUPPORTS_ON): cv.boolean,
        vol.Optional(CONF_STANDBY_TIME): vol.In([20, 60]),
    }
)


def get_ip_mode(host):
    """Get the 'mode' used to retrieve the MAC address."""
    try:
        ip_address = ipaddress.ip_address(host)
    except ValueError:
        return "hostname"

    if ip_address.version == 6:
        return "ip6"
    return "ip"


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the KEF platform."""

    host = config[CONF_HOST]
    mode = get_ip_mode(host)
    mac = await hass.async_add_executor_job(partial(get_mac_address, **{mode: host}))
    if mac is None or mac == "00:00:00:00:00:00":
        raise PlatformNotReady("Cannot get the ip address of kef speaker.")

    unique_id = f"kef-{mac}"

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={**config, "unique_id": unique_id},
        )
    )

    async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        breaks_in_ha_version="2026.1.0",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={
            "domain": DOMAIN,
            "integration_title": "KEF",
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KEFConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the platform from a config entry."""
    client = entry.runtime_data

    async_add_entities(
        [
            KefMediaPlayer(
                client,
                entry.title,
                entry.options[CONF_SUPPORTS_ON],
                SOURCES[entry.data[CONF_TYPE]],
                entry.data[CONF_TYPE],
                entry.entry_id,
            )
        ]
    )

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_MODE,
        {
            vol.Optional("desk_mode"): cv.boolean,
            vol.Optional("wall_mode"): cv.boolean,
            vol.Optional("phase_correction"): cv.boolean,
            vol.Optional("high_pass"): cv.boolean,
            vol.Optional("sub_polarity"): vol.In(["-", "+"]),
            vol.Optional("bass_extension"): vol.In(["Less", "Standard", "Extra"]),
        },
        "set_mode",
    )
    platform.async_register_entity_service(SERVICE_UPDATE_DSP, None, "update_dsp")

    def add_service(name, which, option):
        options = DSP_OPTION_MAPPING[which]
        dtype = type(options[0])  # int or float
        platform.async_register_entity_service(
            name,
            {
                vol.Required(option): vol.All(
                    vol.Coerce(float), vol.Coerce(dtype), vol.In(options)
                )
            },
            f"set_{which}",
        )

    add_service(SERVICE_DESK_DB, "desk_db", "db_value")
    add_service(SERVICE_WALL_DB, "wall_db", "db_value")
    add_service(SERVICE_TREBLE_DB, "treble_db", "db_value")
    add_service(SERVICE_HIGH_HZ, "high_hz", "hz_value")
    add_service(SERVICE_LOW_HZ, "low_hz", "hz_value")
    add_service(SERVICE_SUB_DB, "sub_db", "db_value")


class KefMediaPlayer(MediaPlayerEntity):
    """Kef Player Object."""

    _attr_icon = "mdi:speaker-wireless"

    def __init__(
        self,
        speaker: AsyncKefSpeaker,
        name: str,
        supports_on: bool,
        sources: list[str],
        speaker_type: str,
        unique_id: str,
    ) -> None:
        """Initialize the media player."""
        self._attr_name = name
        self._attr_source_list = sources
        self._speaker = speaker
        self._attr_unique_id = unique_id
        self._supports_on = supports_on
        self._speaker_type = speaker_type

        self._attr_available = False
        self._dsp = None
        self._update_dsp_task_remover: CALLBACK_TYPE = None

        self._attr_supported_features = (
            MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.NEXT_TRACK  # only in Bluetooth and Wifi
            | MediaPlayerEntityFeature.PAUSE  # only in Bluetooth and Wifi
            | MediaPlayerEntityFeature.PLAY  # only in Bluetooth and Wifi
            | MediaPlayerEntityFeature.PREVIOUS_TRACK  # only in Bluetooth and Wifi
        )
        if supports_on:
            self._attr_supported_features |= MediaPlayerEntityFeature.TURN_ON

    async def async_update(self) -> None:
        """Update latest state."""
        _LOGGER.debug("Running async_update")
        try:
            self._attr_available = await self._speaker.is_online()
            if self.available:
                (
                    self._attr_volume_level,
                    self._attr_is_volume_muted,
                ) = await self._speaker.get_volume_and_is_muted()
                state = await self._speaker.get_state()
                self._attr_source = state.source
                self._attr_state = (
                    MediaPlayerState.ON if state.is_on else MediaPlayerState.OFF
                )
                if self._dsp is None:
                    # Only do this when necessary because it is a slow operation
                    await self.update_dsp()
            else:
                self._attr_is_volume_muted = None
                self._attr_source = None
                self._attr_volume_level = None
                self._attr_state = MediaPlayerState.OFF
        except (ConnectionError, TimeoutError) as err:
            _LOGGER.debug("Error in `update`: %s", err)
            self._attr_state = None

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self._speaker.turn_off()

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        if not self._supports_on:
            raise NotImplementedError
        await self._speaker.turn_on()

    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        await self._speaker.increase_volume()

    async def async_volume_down(self) -> None:
        """Volume down the media player."""
        await self._speaker.decrease_volume()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self._speaker.set_volume(volume)

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (True) or unmute (False) media player."""
        if mute:
            await self._speaker.mute()
        else:
            await self._speaker.unmute()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        if self.source_list is not None and source in self.source_list:
            await self._speaker.set_source(source)
        else:
            raise ValueError(f"Unknown input source: {source}.")

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._speaker.set_play_pause()

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._speaker.set_play_pause()

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self._speaker.prev_track()

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._speaker.next_track()

    async def update_dsp(self, _=None) -> None:
        """Update the DSP settings."""
        if self._speaker_type == "LS50" and self.state == MediaPlayerState.OFF:
            # The LSX is able to respond when off the LS50 has to be on.
            return

        mode = await self._speaker.get_mode()
        self._dsp = {
            "desk_db": await self._speaker.get_desk_db(),
            "wall_db": await self._speaker.get_wall_db(),
            "treble_db": await self._speaker.get_treble_db(),
            "high_hz": await self._speaker.get_high_hz(),
            "low_hz": await self._speaker.get_low_hz(),
            "sub_db": await self._speaker.get_sub_db(),
            **mode._asdict(),
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to DSP updates."""
        self._update_dsp_task_remover = async_track_time_interval(
            self.hass, self.update_dsp, DSP_SCAN_INTERVAL
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe to DSP updates."""
        self._update_dsp_task_remover()
        self._update_dsp_task_remover = None

    @property
    def extra_state_attributes(self):
        """Return the DSP settings of the KEF device."""
        return self._dsp or {}

    async def set_mode(
        self,
        desk_mode=None,
        wall_mode=None,
        phase_correction=None,
        high_pass=None,
        sub_polarity=None,
        bass_extension=None,
    ):
        """Set the speaker mode."""
        await self._speaker.set_mode(
            desk_mode=desk_mode,
            wall_mode=wall_mode,
            phase_correction=phase_correction,
            high_pass=high_pass,
            sub_polarity=sub_polarity,
            bass_extension=bass_extension,
        )
        self._dsp = None

    async def set_desk_db(self, db_value):
        """Set desk_db of the KEF speakers."""
        await self._speaker.set_desk_db(db_value)
        self._dsp = None

    async def set_wall_db(self, db_value):
        """Set wall_db of the KEF speakers."""
        await self._speaker.set_wall_db(db_value)
        self._dsp = None

    async def set_treble_db(self, db_value):
        """Set treble_db of the KEF speakers."""
        await self._speaker.set_treble_db(db_value)
        self._dsp = None

    async def set_high_hz(self, hz_value):
        """Set high_hz of the KEF speakers."""
        await self._speaker.set_high_hz(hz_value)
        self._dsp = None

    async def set_low_hz(self, hz_value):
        """Set low_hz of the KEF speakers."""
        await self._speaker.set_low_hz(hz_value)
        self._dsp = None

    async def set_sub_db(self, db_value):
        """Set sub_db of the KEF speakers."""
        await self._speaker.set_sub_db(db_value)
        self._dsp = None
