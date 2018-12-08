import logging
import polling
import json
import xmljson
import lxml
from lxml import etree as ET

import voluptuous as vol

from datetime import timedelta
from bs4 import BeautifulSoup
import requests

from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA,  STATE_ON, STATE_OFF,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_ON_OFF)
from homeassistant.const import (
    CONF_ID, CONF_NAME, ATTR_TEMPERATURE, CONF_PASSWORD,
    CONF_USERNAME, TEMP_CELSIUS)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)

#: Interval in hours that module will try to refresh data from the climote.
CONF_REFRESH_INTERVAL = 'refresh_interval'

NOCHANGE = 'nochange'
DOMAIN = 'climote'
ICON = "mdi:thermometer"

MAX_TEMP = 35
MIN_TEMP = 5

SUPPORT_FLAGS = (SUPPORT_ON_OFF | SUPPORT_TARGET_TEMPERATURE)

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_ID): cv.positive_int,
    vol.Optional(CONF_NAME): cv.string,
}, extra=vol.ALLOW_EXTRA)


def validate_name(config):
    """Validate device name."""
    if CONF_NAME in config:
        return config
    climoteid = config[CONF_ID]
    name = 'climote_{}'.format(climoteid)
    config[CONF_NAME] = name
    return config


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_REFRESH_INTERVAL, default=24): cv.string,
})


async def async_setup_platform(hass, config, add_entities,
                               discovery_info=None):
    """Set up the climote platform."""
    _LOGGER.info('Setting up climote platform')
    _LOGGER.info('usernamekey:%s', CONF_USERNAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    interval = int(config.get(CONF_REFRESH_INTERVAL))

    # Add devices
    climote = ClimoteService(username, password)
    if not (climote.initialize()):
        return False

    entities = []
    for id, name in climote.zones.items():
        entities.append(Climote(climote, id, name, interval))
    add_entities(entities)


class Climote(ClimateDevice):
    """Representation of a Climote device."""

    def __init__(self, climoteService, zoneid, name, interval):
        """Initialize the thermostat."""
        _LOGGER.info('Initialize Climote Entiry')
        self._climote = climoteService
        self._zoneid = zoneid
        self._name = name
        self._force_update = False
        self.throttled_update = Throttle(timedelta(hours=interval))(self._throttled_update)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS | SUPPORT_ON_OFF | SUPPORT_TARGET_TEMPERATURE

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
        zone = "zone" + str(self._zoneid)
        _LOGGER.info("current_temperature: Zone: %s, Temp %s C",
                     zone, self._climote.data[zone]["temperature"])
        return int(self._climote.data[zone]["temperature"]) \
            if self._climote.data[zone]["temperature"] != 'n/a' else 0

    @property
    def is_on(self):
        """Return current operation. ie. heat, idle."""
        zone = "zone" + str(self._zoneid)
        return True if self._climote.data[zone]["status"] == '5' else False

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
        zone = "zone" + str(self._zoneid)
        _LOGGER.info("target_temperature: %s",
                     self._climote.data[zone]["thermostat"])
        return int(self._climote.data[zone]["thermostat"])

    @property
    def current_operation(self):
        """Return current operation."""
        zone = "zone" + str(self._zoneid)
        return STATE_ON if self._climote.data[zone]["status"] == '5' \
                           else STATE_OFF

    def turn_on(self):
        """Turn Heating Boost On."""
        res = self._climote.boost(self._zoneid, 1)
        self._force_update = True
        return res

    def turn_off(self):
        """Turn Heating Boost Off."""
        res = self._climote.boost(self._zoneid, 0)
        if(res):
            self._force_update = True
        return res

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        res = self._climote.set_target_temperature(1, temperature)
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


class IllegalStateException(RuntimeError):
    def __init__(self, arg):
        self.args = arg


_DEFAULT_JSON = (
    '{ "holiday": "00", "hold": null, "updated_at": "00:00", '
    '"unit_time": "00:00", "zone1": { "burner": 0, "status": null, '
    '"temperature": "0", "thermostat": 0 }, "zone2": { "burner": 0, '
    '"status": "0", "temperature": "0", "thermostat": 0 }, '
    '"zone3": { "burner": 0, "status": null, "temperature": "0", '
    '"thermostat": 0 } }')
_LOGIN_URL = 'https://climote.climote.ie/manager/login'
_LOGOUT_URL = 'https://climote.climote.ie/manager/logout'
_SCHEDULE_ELEMENT = '/manager/edit-heating-schedule?heatingScheduleId'

_STATUS_URL = 'https://climote.climote.ie/manager/get-status'
_STATUS_FORCE_URL = _STATUS_URL + '?force=1'
_STATUS_RESPONSE_URL = ('https://climote.climote.ie/manager/'
                        'waiting-get-status-response')
_BOOST_URL = 'https://climote.climote.ie/manager/boost'
_SET_TEMP_URL = 'https://climote.climote.ie/manager/temperature'
_GET_SCHEDULE_URL = ('https://climote.climote.ie/manager/'
                     'get-heating-schedule?heatingScheduleId=')


class ClimoteService:

    def __init__(self, username, password):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent':
                               'Mozilla/5.0 Home Assistant Climote Service'})
        self.config_id = None
        self.config = None
        self.logged_in = False
        self.creds = {'password': username, 'username': password}
        self.data = json.loads(_DEFAULT_JSON)
        self.zones = None

    def initialize(self):
        try:
            self.__login()
            self.__setConfig()
            self.__setZones()
            # if not self.__updateStatus(False):
            #    self.__updateStatus(True)
            return True if(self.config is not None) else False
        finally:
            self.__logout()

    def __login(self):
        r = self.s.post(_LOGIN_URL, data=self.creds)
        if(r.status_code == requests.codes.ok):
            # Parse the content
            soup = BeautifulSoup(r.content, "lxml")
            input = soup.find("input")  # First input has token "cs_token_rf"
            if (len(input['value']) < 2):
                return False
            self.logged_in = True
            self.token = input['value']
            _LOGGER.info("Token: %s", self.token)
            anchors = soup.findAll("a", href=True)
            for a in anchors:
                href = a['href']
                str = href
                if (str.startswith(_SCHEDULE_ELEMENT)):
                    cut = str.find('&startday')
                    str2 = str[:-(len(str)-cut)]
                    self.config_id = str2[49:]
                    _LOGGER.debug('heatingScheduleId:%s', self.config_id)
            return self.logged_in

    def __logout(self):
        _LOGGER.info('Logging Out')
        r = self.s.get(_LOGOUT_URL)
        _LOGGER.debug('Logging Out Result: %s', r.status_code)
        return r.status_code == requests.codes.ok

    def boost(self, zoneid, time):
        _LOGGER.info('Boosting Zone %s', zoneid)
        return self.__boost(zoneid, time)

    def updateStatus(self, force):
        try:
            self.__login()
            self.__updateStatus(force)
        finally:
            self.__logout()

    def __updateStatus(self, force):
        def is_done(r):
            return r.text != '0'
        res = None
        tmp = self.s.headers
        try:
            # Make the initial request (force the update)
            if(force):
                r = self.s.post(_STATUS_FORCE_URL, data=self.creds)
            else:
                r = self.s.post(_STATUS_URL, data=self.creds)

            # Poll for the actual result. It happens over SMS so takes a while
            self.s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
            r = polling.poll(
                lambda: self.s.post(_STATUS_RESPONSE_URL,
                                    data=self.creds),
                step=10,
                check_success=is_done,
                poll_forever=False,
                timeout=120
            )
            if(r.text == '0'):
                res = False
            else:
                self.data = json.loads(r.text)
                _LOGGER.info('Data Response %s', self.data)
                res = True
        except polling.TimeoutException:
            res = False
        finally:
            self.s.headers = tmp
        return res

    def __setConfig(self):
        if(self.logged_in is False):
            raise IllegalStateException("Not logged in")

        r = self.s.get(_GET_SCHEDULE_URL
                       + self.config_id)
        data = r.content
        xml = ET.fromstring(data)
        self.config = xmljson.parker.data(xml)
        _LOGGER.debug('Config:%s', self.config)

    def __setZones(self):
        if(self.config is None):
            return

        zones = {}
        i = 0
        _LOGGER.debug('zoneInfo: %s', self.config["zoneInfo"]["zone"])
        for zone in self.config["zoneInfo"]["zone"]:
            i += 1
            if(zone["active"] == 1):
                zones[i] = zone["label"]
        self.zones = zones

    def set_target_temperature(self, zone, temp):
        _LOGGER.debug('set_temperature zome:%s, temp:%s', zone, temp)
        res = False
        try:
            self.__login()
            data = {
                'temp-set-input[' + str(zone) + ']': temp,
                'do': 'Set',
                'cs_token_rf': self.token
            }
            r = self.s.post(_SET_TEMP_URL=data)
            _LOGGER.info('set_temperature: %d', r.status_code)
            res = r.status_code == requests.codes.ok
        finally:
            self.__logout()
        return res

    def __boost(self, zoneid, time):
        """Turn on the heat for a given zone, for a given number of hours"""
        res = False
        try:
            self.__login()
            data = {
                'zoneIds[' + str(zoneid) + ']': time,
                'cs_token_rf': self.token
            }
            r = self.s.post(_BOOST_URL, data=data)
            _LOGGER.info('Boosting Result: %d', r.status_code)
            res = r.status_code == requests.codes.ok
        finally:
            self.__logout()
        return res
