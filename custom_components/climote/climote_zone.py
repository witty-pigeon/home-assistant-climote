import logging
import polling
from .const import (ICON, MAX_TEMP, MIN_TEMP)
from datetime import timedelta
from homeassistant.util import Throttle
from homeassistant.components.climate import (ClimateEntity)
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,CURRENT_HVAC_HEAT,CURRENT_HVAC_IDLE)
from homeassistant.const import (ATTR_TEMPERATURE, TEMP_CELSIUS)

_LOGGER = logging.getLogger(__name__)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]

class ClimoteZone(ClimateEntity):
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
        _LOGGER.info(
            "current_temperature: Zone: %s, Temp %s C",
            zone,
            self._climote.data[zone]["temperature"]
        )
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

    async def async_set_hvac_mode(self,hvac_mode):
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

    async def async_set_temperature(self, **kwargs):
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
