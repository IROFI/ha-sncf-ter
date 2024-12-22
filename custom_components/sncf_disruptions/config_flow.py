"""Config flow for SNCF Disruptions."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_STATION1_ID,
    CONF_STATION1_NAME,
    CONF_STATION2_ID,
    CONF_STATION2_NAME,
    DEFAULT_NAME,
)

class SNCFDisruptionsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SNCF Disruptions."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_TOKEN): str,
                vol.Required(CONF_STATION1_ID): str,
                vol.Required(CONF_STATION1_NAME): str,
                vol.Required(CONF_STATION2_ID): str,
                vol.Required(CONF_STATION2_NAME): str,
            }),
            errors=errors,
        ) 