from bs4 import BeautifulSoup
import logging
import requests
import json
import xmljson
import lxml

_LOGGER = logging.getLogger(__name__)

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
    def __init__(self, username, password, passcode):
        self.s = requests.Session()
        self.s.headers.update({'User-Agent':
                               'Mozilla/5.0 Home Assistant Climote Service'})
        self.config_id = None
        self.config = None
        self.logged_in = False
        self.creds = {'password': username, 'username': passcode, 'passcode':password}
        self.data = json.loads(_DEFAULT_JSON)
        self.zones = None

    async def populate(self):
        try:
            await self.__login()
            await self.__setConfig()
            self.__setZones()
            # if not self.__updateStatus(False):
            #    self.__updateStatus(True)
            return True if(self.config is not None) else False
        finally:
            await self.__logout()

    async def __login(self):
        r = await self.s.post(_LOGIN_URL, data=self.creds)
        if(r.status_code == requests.codes.ok):
            # Parse the content
            soup = BeautifulSoup(r.content, "lxml")
            input = soup.find("input")  # First input has token "cs_token_rf"
            if (len(input['value']) < 2):
                return False
            self.logged_in = True
            self.token = input['value']
            _LOGGER.info("Token: %s", self.token)
            str = r.text
            sched = str.find(_SCHEDULE_ELEMENT)
            if (sched):
                cut = str.find('&startday',sched)
                str2 = str[sched:-(len(str)-cut)]
                self.config_id = str2[49:]
                _LOGGER.debug('heatingScheduleId:%s', self.config_id)
            return self.logged_in

    async def __logout(self):
        _LOGGER.info('Logging Out')
        r = await self.s.get(_LOGOUT_URL)
        _LOGGER.debug('Logging Out Result: %s', r.status_code)
        return r.status_code == requests.codes.ok

    async def boost(self, zoneid, time):
        _LOGGER.info('Boosting Zone %s', zoneid)
        return await self.__boost(zoneid, time)

    async def updateStatus(self, force):
        _LOGGER.info('Updating status')
        try:
            await self.__login()
            await self.__updateStatus(force)
        finally:
            await self.__logout()

    async def __updateStatus(self, force):
        def is_done(r):
            return r.text != '0'
        res = None
        tmp = self.s.headers
        try:
            # Make the initial request (force the update)
            if(force):
                r = await self.s.post(_STATUS_FORCE_URL, data=self.creds)
            else:
                r = await self.s.post(_STATUS_URL, data=self.creds)

            # Poll for the actual result. It happens over SMS so takes a while
            self.s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
            r = await polling.poll(
                lambda: self.s.post(_STATUS_RESPONSE_URL, data=self.creds),
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

    async def __setConfig(self):
        if(self.logged_in is False):
            raise IllegalStateException("Not logged in")

        r = await self.s.get(_GET_SCHEDULE_URL + self.config_id)
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

    async def set_target_temperature(self, zone, temp):
        _LOGGER.debug('set_temperature zome:%s, temp:%s', zone, temp)
        res = False
        try:
            await self.__login()
            data = {
                'temp-set-input[' + str(zone) + ']': temp,
                'do': 'Set',
                'cs_token_rf': self.token
            }
            r = await self.s.post(_SET_TEMP_URL, data=data)
            _LOGGER.info('set_temperature: %d', r.status_code)
            res = r.status_code == requests.codes.ok
        finally:
            await self.__logout()
        return res

    async def __boost(self, zoneid, time):
        """Turn on the heat for a given zone, for a given number of hours"""
        res = False
        try:
            await self.__login()
            data = {
                'zoneIds[' + str(zoneid) + ']': time,
                'cs_token_rf': self.token
            }
            r = await self.s.post(_BOOST_URL, data=data)
            _LOGGER.info('Boosting Result: %d', r.status_code)
            res = r.status_code == requests.codes.ok
        finally:
            await self.__logout()
        return res

class IllegalStateException(RuntimeError):
    def __init__(self, arg):
        self.args = arg
