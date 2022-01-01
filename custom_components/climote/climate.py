from datetime import timedelta
from enum import Enum
import logging
from typing import Any, Callable, Dict, List, Optional

from homeassistant import config_entries, core
from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
import voluptuous as vol

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID
from .climote_service import ClimoteService
from .climote_zone import ClimoteZone

_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    climote = build_climote_service(config)
    devices = await get_devices(climote, hass)
    async_add_entities(devices, update_before_add=True)

# async def async_setup_platform(
    # hass: HomeAssistantType,
    # config: ConfigType,
    # add_entities: Callable,
    # discovery_info: Optional[DiscoveryInfoType] = None,
# ) -> None:
    # climote = build_climote_service(config)
    # devices = await get_devices(climote)
    # add_entities(devices)

async def get_devices(climote,hass):
    devices = []

    zones = await hass.async_add_executor_job(lambda: climote.populate())
    if climote.zones is None:
        _LOGGER.info("Climote devices: None")
        return devices

    _LOGGER.info("Climote devices zones: %", zones)
    for zone_id, name in climote.zones.items():
        interval = 1
        cz = ClimoteZone(climote, zone_id, name, interval, hass)
        _LOGGER.info("Climote device: Adding %s", str(cz))
        devices.append(cz)

    _LOGGER.info("Climote devices " + str(devices) + " " + str(len(devices)))
    return devices

def build_climote_service(config) -> ClimoteService:
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    device_id = config[CONF_DEVICE_ID]

    return ClimoteService(username, password, device_id)
