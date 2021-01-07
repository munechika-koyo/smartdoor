from smartdoor import SmartDoor
from logging import getLogger


# Set log
log = getLogger(__name__)

# Define path to conf.yaml
path = "conf.yaml"

# Instansionate
door = SmartDoor(path=path, log=log)

# Set initial key status
door.locked = False

# SmartDoor seaquence starts
try:
    while True:
        # Wait for NFC card toched
        tag = door.wait_for_touch()

        # If buttom is pushed
        if tag is None:
            door.PWM_switch_LED.ChangeDutyCycle(50)
            door.doorSeaquence(user="誰か")
            door.PWM_switch_LED.ChangeDutyCycle(100)
            continue

        # If NFC card is detected
        elif bool(tag):
            # Authentication of user idm
            user = door.authenticate(tag)

            # If invalid user is detected
            if user is None:
                door.warning()
                continue

            # If authentication completed
            else:
                door.doorSeaquence(user=user)

        # If keyInterrupt (tag == False)
        else:
            # Not implemented yet when interrupting
            raise KeyboardInterrupt

finally:
    door.close()
