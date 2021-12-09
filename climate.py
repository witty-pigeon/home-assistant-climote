import logging
import polling
from .climote_service import ClimoteService

import voluptuous as vol

from datetime import timedelta

from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import (
    ClimateEntity, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (SUPPORT_TARGET_TEMPERATURE, HVAC_MODE_OFF, HVAC_MODE_HEAT,CURRENT_HVAC_HEAT,CURRENT_HVAC_IDLE)
from homeassistant.const import (
    CONF_ID, CONF_NAME, ATTR_TEMPERATURE, CONF_PASSWORD,
    CONF_USERNAME, TEMP_CELSIUS, CONF_DEVICES)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)

#: Interval in hours that module will try to refresh data from the climote.
CONF_REFRESH_INTERVAL = 'refresh_interval'

NOCHANGE = 'nochange'
DOMAIN = 'climote'
ICON = "mdi:thermometer"

MAX_TEMP = 35
MIN_TEMP = 5

#SUPPORT_FLAGS = (SUPPORT_ON_OFF | SUPPORT_TARGET_TEMPERATURE)
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]

#DEVICE_SCHEMA = vol.Schema({
#    vol.Required(CONF_ID): cv.positive_int,
#    vol.Optional(CONF_NAME): cv.string,
#}, extra=vol.ALLOW_EXTRA)


def validate_name(config):
    """Validate device name."""
    if CONF_NAME in config:
        return config
    climoteId = config[CONF_ID]
    name = 'climote_{}'.format(climoteId)
    config[CONF_NAME] = name
    return config

# CONFIG_SCHEMA = vol.Schema(
    # {
        # DOMAIN: vol.Schema(
            # {
                # vol.Required(CONF_USERNAME): cv.string,
                # vol.Required(CONF_PASSWORD): cv.string,
                # vol.Required(CONF_ID): cv.string,
                # vol.Optional(CONF_REFRESH_INTERVAL, default=24): cv.string,
            # }
        # )
    # },
    # extra=vol.ALLOW_EXTRA,
# )

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
   vol.Required(CONF_USERNAME): cv.string,
   vol.Required(CONF_PASSWORD): cv.string,
   vol.Required(CONF_ID): cv.string,
   vol.Optional(CONF_REFRESH_INTERVAL, default=24): cv.string,
#   vol.Required(CONF_DEVICES):
#       vol.Schema({cv.string: DEVICE_SCHEMA})
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the ephember thermostat."""
    _LOGGER.info('Setting up climote platform')
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    climoteID = config.get(CONF_ID)


    interval = int(config.get(CONF_REFRESH_INTERVAL))

    # Add devices
    climote = ClimoteService(username, password, climoteID)
    if not (await climote.initialize()):
        return False

    entities = []
    for id, name in climote.zones.items():
        c = Climote(climote, id, name, interval)
        await c.throttled_update_a
        entities.append(c)
    async_add_entities(entities)

    return

class Climote(ClimateEntity):
    """Representation of a Climote device."""

    def __init__(self, climoteService, zoneId, name, interval):
        """Initialize the thermostat."""
        _LOGGER.info('Initialize Climote Entity')
        self._climote = climoteService
        self._zoneId = zoneId
        self._name = name
        self._force_update = False
        self._interval = interval

    async def throttled_update_a(self):
        self.throttled_update = Throttle(timedelta(hours=self.interval))(self._throttled_update)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def hvac_mode(self):
#        """Return current operation ie. heat, cool, idle."""
#        return 'idle'
        """Return current operation. ie. heat, idle."""
        zone = "zone" + str(self._zoneId)
        return 'heat' if self._climote.data[zone]["status"] == '5' else 'idle'

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return SUPPORT_MODES

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def current_temperature(self):
        zone = "zone" + str(self._zoneId)
        _LOGGER.info("current_temperature: Zone: %s, Temp %s C",
                     zone, self._climote.data[zone]["temperature"])
        return int(self._climote.data[zone]["temperature"]) \
            if self._climote.data[zone]["temperature"] != 'n/a' else 0

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        zone = "zone" + str(self._zoneId)
        _LOGGER.info("target_temperature: %s",
                     self._climote.data[zone]["thermostat"])
        return int(self._climote.data[zone]["thermostat"])

    @property
    def hvac_action(self):
        """Return current operation."""
        zone = "zone" + str(self._zoneId)
        return CURRENT_HVAC_HEAT if self._climote.data[zone]["status"] == '5' \
                           else CURRENT_HVAC_IDLE

    async def set_hvac_mode(self,hvac_mode):
        if(hvac_mode==HVAC_MODE_HEAT):
            """Turn Heating Boost On."""
            res = await self._climote.boost(self._zoneId, 1)
            self._force_update = True
            return res
        if(hvac_mode==HVAC_MODE_OFF):
            """Turn Heating Boost Off."""
            res = await self._climote.boost(self._zoneId, 0)
            if(res):
                self._force_update = True
            return res

    async def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        res = await self._climote.set_target_temperature(1, temperature)
        if(res):
            self._force_update = True
        return res

    async def async_update(self):
        """Get the latest state from the thermostat."""
        if self._force_update:
            await self.throttled_update(no_throttle=True)
            self._force_update = False
        else:
            await self.throttled_update(no_throttle=False)

    async def _throttled_update(self, **kwargs):
        """Get the latest state from the thermostat with a throttle."""
        _LOGGER.info("_throttled_update Force: %s", self._force_update)
        self._climote.updateStatus(self._force_update)
