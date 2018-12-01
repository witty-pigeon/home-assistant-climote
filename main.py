from climote import ClimoteService
import logging

logging.basicConfig(format='%(levelname)s - %(asctime)s - %(message)s', level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)

cs = ClimoteService('fionnghualar@hotmail.com', '0879552708')

try:
    cs.login()
    # cs.boostHeating(1)
    # cs.boostWater(0)
    # temp = cs.readTemperature()
    # print temp
    cs.getStatus(True)
    _LOGGER.info("Temp: %s", cs.data["zone1"]["temperature"])
finally:
    cs.logout()
