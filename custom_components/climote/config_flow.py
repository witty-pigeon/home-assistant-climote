from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries, core, data_entry_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get_registry,
)

from .climote_service import ClimoteService
import voluptuous as vol

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = {
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Required(CONF_DEVICE_ID): str,
}

class ClimoteCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    # (this is not implemented yet)
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.config = {}
        self.climote_service = None
        self._errors = {}

    async def async_step_user(self, user_input=None):
        self._errors = {}

        if not user_input:
            return self._show_initial_form()

        self._save_user_input_to_config(user_input=user_input)

        try:
            self._config_climote_service()
        except KeyError as err:
            _LOGGER.error("Error configuring climote service: %s", err)
            self._errors["base"] = "missing_field"
            return self._show_initial_form()

        try:
            await self.hass.async_add_executor_job(
                self.climote_service.populate
            )
        except BaseException as err:
            _LOGGER.error("Error populating: %s, %s", self.climote_service.zones, err)
            self._errors["base"] = "no zones"
            return self._show_initial_form()

        if self.climote_service.zones == None or len(self.climote_service.zones) < 1:
            _LOGGER.error("Error no zones: %s", self.climote_service.zones)
            self._errors["base"] = "no zones"
            return self._show_initial_form()

        return self.async_create_entry(
            title="Add climote zones",
            data=user_input,
        )


    def _show_initial_form(self):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(DATA_SCHEMA),
            errors=self._errors)

    def _config_climote_service(self) -> None:
        """Configure the climote service with the saved user input."""
        self.climote_service = ClimoteService(
            self.config[CONF_USERNAME],
            self.config[CONF_PASSWORD],
            self.config[CONF_DEVICE_ID],
        )

    def _save_user_input_to_config(self, user_input=None) -> None:
        """Process user_input to save to self.config.
        user_input can be a dictionary of strings or an internally
        saved config_entry data entry. This function will convert all to internal strings.
        """
        if user_input is None:
            return

        self.config = user_input
