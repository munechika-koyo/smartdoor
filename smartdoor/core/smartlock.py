"""Module for SmartLock class"""
from time import sleep
from gpiozero import LED, Buzzer, Button, Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from logging import getLogger


logger = getLogger(__name__)
factory = PiGPIOFactory()


class SmartLock:
    """This class is used to control raspberry Pi's GPIO devices (LEDs, Buzzer, servomotor, etc.).

    Parameters
    ----------
    pins
        pin assignment key-value map

        The following keys must be included:

        - switch: input signal from switch
        - LED_red : output signal to red LED
        - LED_green : output signal to green LED
        - LED_switch : output signal to switch LED
        - buzzer : output signal to buzzer
        - servo : output signal to servomotor

    Methods
    -------
    lock()
        excute lock seaquence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
    unlock()
        excute unlock seaquence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
    """
    def __init__(self, pins: dict[str, int]) -> None:
        # validate pin assignment
        self.pins = pins

        # Initialize GPIO devices
        # === LED ===
        self.led_red = LED(pins["LED_red"])
        self.led_green = LED(pins["LED_green"])
        self.led_switch = LED(pins["LED_switch"])

        # === Push button switch ===
        self.switch = Button(pins["switch"])

        # === Buzzer ===
        self.buzzer = Buzzer(pins["buzzer"])

        # === Servo ===
        self.servo = Servo(pins["servo"], pin_factory=factory)

        # initialize locked property to avoid unexpected behavior
        self._locked = False

    @property
    def pins(self) -> dict[str, int]:
        """pins asssignment map
        """
        return self._pins

    @pins.setter
    def pins(self, value):
        if not isinstance(value, dict):
            raise TypeError("pins must be dict type.")
        
        # validate pin assignment
        self._check_pin_overlap()
        self._pins = value

    @property
    def locked(self) -> bool:
        """key's status

        If true, the key is locked now, otherwise unlocked

        Returns
        -------
        bool
            key's status (True: locked, False: unlocked)
        """
        return self._locked

    @locked.setter
    def locked(self, value):
        if not isinstance(value, bool):
            logger.error("locked must be a bool value")
            raise TypeError("locked must be a bool value")
        self._locked = value

    def lock(self) -> None:
        """Excute Locking sequence

        The detail of the sequence is as follows:

        1. Green LED off
        2. Red LED Blinking
        3. buzzer beeping (2 times)
        4. servomotor moving
        5. Red LED on
        """
        # Green LED off
        self.led_green.off()  # switch green LED off

        # Red LED blinking
        self.led_red.blink(on_time=0.125, off_time=0.125)  # blink red LED

        # sound buzzer
        self.buzzer.beep(on_time=0.1, off_time=0.05, n=2, background=True)

        # control servomotor
        self.servo.ChangeDutyCycle(7.5)  # positioning
        sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(2.5)  # rotate 90 deg
        sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(7.5)  # rotate 0 deg
        sleep(0.5)
        self.servo.value = None  # No signal sent

        # Red LED on
        self.led_red.on()  # switch red LED on

        # set lock status
        self.locked = True

    def unlock(self) -> None:
        """Excute unlocking sequence

        The detail of the sequence is as follows:

        1. Red LED off
        2. Green LED Blinking
        3. buzzer beep (3 times)
        4. servomotor moving
        5. Green LED on
        """
        # Red LED off
        self.led_red.off()  # switch red LED off

        # Green LED blinking
        self.led_green.blink(on_time=0.125, off_time=0.125)  # blink green LED

        # sound buzzer
        self.buzzer.beep(on_time=0.1, off_time=0.05, n=3, background=True)

        # control servomotor
        self.PWM_servo.ChangeDutyCycle(7.5)  # positioning
        sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(12.5)  # rotate -90 deg
        sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(7.5)  # rotate 0 deg
        sleep(0.5)
        self.servo.value = None  # No signal sent

        # Green LED on
        self.led_green.on()  # switch green LED on

        # set lock status
        self.locked = False

    def _check_pin_overlap(self):
        """check if pin assignment is overlaped
        """
        # pin numbers
        pin_numbers = [
            num for num in self.pins.values()
        ]

        for pin in pin_numbers:
            if pin_numbers.count(pin) > 1:
                logger.error("detect overlaped pin assignment!")
                raise Exception
