"""Config flow for KEF."""

from typing import Any

from aiokef import AsyncKefSpeaker
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_TYPE
from homeassistant.helpers import config_validation as cv

from .const import (
    DEFAULT_INVERSE_SPEAKER_MODE,
    DEFAULT_MAX_VOLUME,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SUPPORTS_ON,
    DEFAULT_VOLUME_STEP,
    DOMAIN,
)
from .media_player import (
    CONF_INVERSE_SPEAKER_MODE,
    CONF_MAX_VOLUME,
    CONF_STANDBY_TIME,
    CONF_SUPPORTS_ON,
    CONF_VOLUME_STEP,
)


class KEFConfigFlow(ConfigFlow, domain=DOMAIN):
    """KEF config flow."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            client = AsyncKefSpeaker(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                loop=self.hass.loop,
            )
            try:
                await client.is_online()
            except (ConnectionError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data=user_input,
                    options={
                        CONF_MAX_VOLUME: DEFAULT_MAX_VOLUME,
                        CONF_VOLUME_STEP: DEFAULT_VOLUME_STEP,
                        CONF_SUPPORTS_ON: DEFAULT_SUPPORTS_ON,
                        CONF_INVERSE_SPEAKER_MODE: DEFAULT_INVERSE_SPEAKER_MODE,
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_TYPE): vol.In(["LSX", "LS50"]),
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, config: dict[str, Any]) -> ConfigFlowResult:
        """Import a config entry."""
        self._async_abort_entries_match({CONF_HOST: config[CONF_HOST]})
        client = AsyncKefSpeaker(
            config[CONF_HOST],
            config[CONF_PORT],
            loop=self.hass.loop,
        )
        try:
            await client.is_online()
        except (ConnectionError, TimeoutError):
            return self.async_abort(reason="cannot_connect")
        result = self.async_create_entry(
            title=config[CONF_NAME],
            data={
                CONF_HOST: config[CONF_HOST],
                CONF_PORT: config[CONF_PORT],
                CONF_TYPE: config[CONF_TYPE],
            },
            options={
                CONF_MAX_VOLUME: config[CONF_MAX_VOLUME],
                CONF_VOLUME_STEP: config[CONF_VOLUME_STEP],
                CONF_INVERSE_SPEAKER_MODE: config[CONF_INVERSE_SPEAKER_MODE],
                CONF_SUPPORTS_ON: config[CONF_SUPPORTS_ON],
                CONF_STANDBY_TIME: config.get(CONF_STANDBY_TIME),
            },
        )


class KEFOptionsFlowHandler(OptionsFlow):
    """KEF Options flow handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initialize form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not errors:
                return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_MAX_VOLUME, default=DEFAULT_MAX_VOLUME
                        ): cv.small_float,
                        vol.Optional(
                            CONF_VOLUME_STEP, default=DEFAULT_VOLUME_STEP
                        ): cv.small_float,
                        vol.Optional(
                            CONF_INVERSE_SPEAKER_MODE,
                            default=DEFAULT_INVERSE_SPEAKER_MODE,
                        ): cv.boolean,
                        vol.Optional(
                            CONF_SUPPORTS_ON, default=DEFAULT_SUPPORTS_ON
                        ): cv.boolean,
                        vol.Optional(CONF_STANDBY_TIME): vol.In([20, 60]),
                    }
                ),
                user_input or self.config_entry.options,
            ),
        )
