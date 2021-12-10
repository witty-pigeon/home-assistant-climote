from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries, core
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_NAME, CONF_PATH, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get_registry,
)
from .climote_service import ClimoteService
from .climate import PLATFORM_SCHEMA
import voluptuous as vol

from .const import DOMAIN
from homeassistant.const import (
    CONF_ID, CONF_NAME, CONF_PASSWORD, CONF_USERNAME, CONF_DEVICES)

_LOGGER = logging.getLogger(__name__)

async def validate_auth(username: str, password: str, climoteId: str, hass: core.HassJob) -> None:
    """Validates a GitHub access token.
    Raises a ValueError if the auth token is invalid.
    """
    # session = async_get_clientsession(hass)
    climote = ClimoteService(username, password, climoteId)
    await climote.populate()

    if climote.zones == None or len(climote.zones) < 1:
        raise ValueError


class ClimoteCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Climote Custom config flow."""

    data: Optional[Dict[str, Any]]

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                username = user_input[CONF_USERNAME]
                password = user_input[CONF_PASSWORD]
                climoteId = user_input[CONF_ID]
                await validate_auth(username, password, climoteId, self.hass)
            except ValueError:
                errors["base"] = "auth"
            if not errors:
                # Input is valid, set data.
                self.data = user_input

        return self.async_show_form(
            step_id="user", data_schema=PLATFORM_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}
        # Grab all configured repos from the entity registry so we can populate the
        # multi-select dropdown that will allow a user to remove a repo.
        # entity_registry = await async_get_registry(self.hass)
        # entries = async_entries_for_config_entry(
            # entity_registry,
            # self.config_entry.entry_id
        # )
        # Default value for our multi-select.
        # all_repos = {e.entity_id: e.original_name for e in entries}
        # repo_map = {e.entity_id: e for e in entries}

        # if user_input is not None:
            # updated_repos = deepcopy(self.config_entry.data[CONF_REPOS])

            # Remove any unchecked repos.
            # removed_entities = [
                # entity_id
                # for entity_id in repo_map.keys()
                # if entity_id not in user_input["repos"]
            # ]
            # for entity_id in removed_entities:
                # Unregister from HA
                # entity_registry.async_remove(entity_id)
                # Remove from our configured repos.
                # entry = repo_map[entity_id]
                # entry_path = entry.unique_id
                # updated_repos = [e for e in updated_repos if e["path"] != entry_path]

        options_schema  = {
            vol.Required("username"): str,
            vol.Required("password"): str,
        }

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
