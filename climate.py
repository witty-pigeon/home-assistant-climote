import logging
import voluptuous as vol

from .climote_service import ClimoteService
from .climote_zone import ClimoteZone

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import (PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_ID, CONF_NAME, CONF_PASSWORD, CONF_USERNAME, CONF_DEVICES)

_LOGGER = logging.getLogger(__name__)

#: Interval in hours that module will try to refresh data from the climote.
CONF_REFRESH_INTERVAL = 'refresh_interval'

NOCHANGE = 'nochange'
DOMAIN = 'climote'

MAX_TEMP = 35
MIN_TEMP = 5

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
   vol.Required(CONF_USERNAME): cv.string,
   vol.Required(CONF_PASSWORD): cv.string,
   vol.Required(CONF_ID): cv.string,
   vol.Optional(CONF_REFRESH_INTERVAL, default=24): cv.string,
})

def validate_name(config):
    """Validate device name."""
    if CONF_NAME in config:
        return config
    climoteId = config[CONF_ID]
    name = 'climote_{}'.format(climoteId)
    config[CONF_NAME] = name
    return config

async def async_setup_entry(hass, config):
    """Setup up a config entry."""

    _LOGGER.info('Setting up climote platform')
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    climoteID = config.get(CONF_ID)
    interval = int(config.get(CONF_REFRESH_INTERVAL))

    # Add devices
    climote = ClimoteService(username, password, climoteID)
    populatedZones = await climote.populate()

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the climote thermostat."""

    _LOGGER.info('Setting up climote platform')
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    climoteID = config.get(CONF_ID)
    interval = int(config.get(CONF_REFRESH_INTERVAL))

    # Add devices
    climote = ClimoteService(username, password, climoteID)
    populatedZones = await climote.populate()
    if not (populatedZones):
        return False

    entities = []

    for zoneId, name in climote.zones.items():
        c = ClimoteZone(climote, zoneId, name, interval)
        await c.throttled_update_a
        entities.append(c)

    async_add_entities(entities)

    return
