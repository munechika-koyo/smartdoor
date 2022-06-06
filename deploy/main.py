import os
from smartdoor import SmartDoor
from logging import config, getLogger
import urllib3
from urllib3.exceptions import InsecureRequestWarning


# set invisible of https secure warning
urllib3.disable_warnings(InsecureRequestWarning)

# Base Path
DIR = os.path.dirname(__file__)

# Set logger
config.fileConfig(os.path.join(DIR, "logging.conf"))
logger = getLogger()

# Define path to conf.yaml
path = os.path.join(DIR, "conf.yaml")

# Instantiate
door = SmartDoor(path=path, log=logger)

# Set initial key status
door.locked = False
logger.info("set initial door status as 'UNLOCKED'")

# SmartDoor seaquence starts
door.start()
try:
    while True:
        # Wait for IC card touched
        logger.info("Waiting NFC card touched...")
        tag = door.wait_ICcard_touched()

        # If buttom is pushed
        if tag is None:
            door.PWM_LED_switch.ChangeDutyCycle(50)
            door.door_sequence(user="スイッチ操作者")
            door.PWM_LED_switch.ChangeDutyCycle(100)
            continue

        # If IC card is detected
        elif bool(tag):
            # Authentication of user idm
            user = door.authenticate(tag)

            # If invalid user is detected
            if user is None:
                door.warning_invalid_touch()
                continue

            # If authentication completed
            else:
                door.door_sequence(user=user)

        # If keyInterrupt (tag == False)
        else:
            # Not implemented yet when interrupting
            logger.info("tag == false")
            break

except Exception as e:
    logger.error(e)

finally:
    logger.info("Cleaning up...")
    door.close()
