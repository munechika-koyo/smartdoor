"""Module for SmartLock class."""
from __future__ import annotations

from logging import getLogger
from time import sleep

from gpiozero import LED, Button, Buzzer, Device, Servo

module_logger = getLogger(__name__)


class SmartLock:
    """This class is used to control raspberry Pi's GPIO devices (LEDs, Buzzer, servomotor, etc.).

    Parameters
    ----------
    pins
        pin assignment key-value map. A pin number must be GPIO pin not BCM one.

        The following keys must be included:

        - button: input signal from push button switch
        - LED_red : output signal to red LED
        - LED_green : output signal to green LED
        - LED_button : output signal to button switch LED
        - buzzer : output signal to buzzer
        - servo : output signal to servomotor

    Methods
    -------
    lock()
        excute lock seaquence
        (LED blinking -> buzzer beeping -> servomotor moving -> LED lighting)
    unlock()
        excute unlock seaquence
        (LED blinking -> buzzer beeping -> servomotor moving -> LED lighting)
    """

    # define class logger
    logger = getLogger("main").getChild("SmartLock")

    def __init__(self, pins: dict[str, int]) -> None:
        # set pin factory
        try:
            from gpiozero.pins.pigpio import PiGPIOFactory

            Device.pin_factory = PiGPIOFactory()
            self.logger.debug("using pigpio pin factory")

        except ModuleNotFoundError:
            self.logger.debug("using defalut pin factory")

        # validate pin assignment
        self.pins = pins

        # Initialize GPIO devices
        # === LED ===
        self.led_red = LED(pins["LED_red"])
        self.led_green = LED(pins["LED_green"])
        self.led_button = LED(pins["LED_button"])

        # === Push button switch ===
        self.button = Button(pins["button"])

        # === Buzzer ===
        self.buzzer = Buzzer(pins["buzzer"])

        # === Servo ===
        self.servo = Servo(
            pins["servo"],
            initial_value=None,
            min_pulse_width=0.5e-3,
            max_pulse_width=2.4e-3,
        )

        # initialize locked property to avoid unexpected behavior
        self._locked = False

    @property
    def pins(self) -> dict[str, int]:
        """Pins asssignment map."""
        return self._pins

    @pins.setter
    def pins(self, maps):
        if not isinstance(maps, dict):
            raise TypeError("pins must be dict type.")

        # validate pin assignment
        self._check_pin_overlap(maps)
        self._pins = maps

    @property
    def locked(self) -> bool:
        """Key's status.

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
            raise TypeError("locked must be a bool value")
        self._locked = value

    def lock(self) -> None:
        """Excute Locking sequence.

        The detail of the sequence is as follows:

        1. Green LED off
        2. Red LED Blinking
        3. Buzzer beeping (2 times)
        4. Servomotor moving
        5. Red LED on
        """
        self.logger.debug("locking sequence started")

        # Green LED off
        self.led_green.off()

        # Red LED blinking
        self.led_red.blink(on_time=0.2, off_time=0.2)

        # sound buzzer
        self.buzzer.beep(on_time=0.1, off_time=0.05, n=2)

        # control servomotor
        self.servo.min()
        sleep(0.5)
        self.servo.mid()
        sleep(0.5)
        self.servo.detach()  # No signal sent

        # Red LED on
        self.led_red.on()

        # set lock status
        self.locked = True

    def unlock(self) -> None:
        """Excute unlocking sequence.

        The detail of the sequence is as follows:

        1. Red LED off
        2. Green LED Blinking
        3. Buzzer beep (3 times)
        4. Servomotor moving
        5. Green LED on
        """
        self.logger.debug("unlocking sequence started")

        # Red LED off
        self.led_red.off()

        # Green LED blinking
        self.led_green.blink(on_time=0.2, off_time=0.2)

        # sound buzzer
        self.buzzer.beep(on_time=0.1, off_time=0.05, n=3)

        # control servomotor
        self.servo.max()
        sleep(0.5)
        self.servo.mid()
        sleep(0.5)
        self.servo.detach()  # No signal sent

        # Green LED on
        self.led_green.on()

        # set lock status
        self.locked = False

    def _check_pin_overlap(self, maps: dict[str, int]):
        """Check if pin assignment is overlaped."""
        # pin numbers
        pin_numbers = [num for num in maps.values()]

        for pin in pin_numbers:
            if pin_numbers.count(pin) > 1:
                raise Exception("detect overlaped pin assignment!")
