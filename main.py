from climote import ClimoteService
import logging
import json

logging.basicConfig(format='%(levelname)s - %(asctime)s - %(message)s', level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)

json_data = open('config.json').read()
c = json.loads(json_data)

_LOGGER.info("Config: %s", c)

cs = ClimoteService(c["username"], c["password"])

cs.initialize()
# cs.login()
# cs.boostHeating(0)
_LOGGER.info("Zones: %s", cs.zones)
# cs.boostWater(0)
# temp = cs.readTemperature()
# print temp
# cs.getConfig()
# cs.getStatus(False)
# _LOGGER.info("Temp: %s", cs.data["zone1"]["temperature"])
