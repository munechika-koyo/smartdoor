
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)  # PIN number is used, not GPIO


class SmartLock:
    """ SmartLock class
    This is used to initiate and control raspi GPIO pins, PWM (LED, servomotor), etc.

    Parameters
    ----------

    methods
    -------
    lock()
        excute lock seaquence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
    unlock()
        excute unlock seaquence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
    """
    def __init__(self, pin_switch=None, pin_LED_red=None, pin_LED_green=None, pin_LED_switch=None, pin_buzzer=None, pin_servo=None) -> None:
        # configure pin assignment property
        self.pin_switch = pin_switch
        self.pin_LED_red = pin_LED_red
        self.pin_LED_green = pin_LED_green
        self.pin_LED_switch = pin_LED_switch
        self.pin_buzzer = pin_buzzer
        self.pin_servo = pin_servo

        # check if pin number overlaps with others
        self._check_pin_overlap()

        # initialize pin setup
        GPIO.setup(self.pin_switch, GPIO.IN)
        GPIO.setup(self.pin_LED_red, GPIO.OUT)
        GPIO.setup(self.pin_LED_green, GPIO.OUT)
        GPIO.setup(self.pin_LED_switch, GPIO.OUT)
        GPIO.setup(self.pin_buzzer, GPIO.OUT)
        GPIO.setup(self.pin_servo, GPIO.OUT)

        # initialize PWM objects
        self._PWM_LED_red = GPIO.PWM(self.pin_LED_red, 5)  # 5Hz PWM
        self._PWM_LED_green = GPIO.PWM(self.pin_LED_green, 5)
        self._PWM_LED_switch = GPIO.PWM(self.pin_LED_switch, 5)
        self._PWM_servo = GPIO.PWM(self.pin_servo, 50)  # 50Hz PWM

    @property
    def pin_switch(self):
        """pin number for switch

        Returns
        -------
        int
            pin number
        """
        return self._pin_switch

    @pin_switch.setter
    def pin_switch(self, value):
        if not isinstance(value, int):
            raise ValueError("pin_switch must be integer.")
        self._pin_switch = value

    @property
    def pin_LED_red(self):
        """pin number for red LED

        Returns
        -------
        int
            pin number
        """
        return self._pin_LED_red

    @pin_LED_red.setter
    def pin_LED_red(self, value):
        if not isinstance(value, int):
            raise ValueError("pin_LED_red must be integer.")
        self._pin_LED_red = value

    @property
    def pin_LED_green(self):
        """pin number for green LED

        Returns
        -------
        int
            pin number
        """
        return self._pin_LED_green

    @pin_LED_green.setter
    def pin_LED_green(self, value):
        if not isinstance(value, int):
            raise ValueError("pin_LED_green must be integer.")
        self._pin_LED_green = value

    @property
    def pin_LED_switch(self):
        """pin number for switch LED

        Returns
        -------
        int
            pin number
        """
        return self._pin_LED_switch

    @pin_LED_switch.setter
    def pin_LED_switch(self, value):
        if not isinstance(value, int):
            raise ValueError("pin_LED_switch must be integer.")
        self._pin_LED_switch = value

    @property
    def pin_buzzer(self):
        """pin number for buzzer

        Returns
        -------
        int
            pin number
        """
        return self._pin_buzzer

    @pin_buzzer.setter
    def pin_buzzer(self, value):
        if not isinstance(value, int):
            raise ValueError("pin_buzzer must be integer.")
        self._pin_buzzer = value

    @property
    def pin_servo(self):
        """pin number for servomotor

        Returns
        -------
        int
            pin number
        """
        return self._pin_servo

    @pin_servo.setter
    def pin_servo(self, value):
        if not isinstance(value, int):
            raise ValueError("pin_servo must be integer.")
        self._pin_servo = value

    @property
    def PWM_LED_red(self):
        """PWM instanse for red LED

        Returns
        -------
        GPIO PWM
            instanse for GPIO PWM
        """
        return self._PWM_LED_red

    @property
    def PWM_LED_green(self):
        """PWM instanse for green LED

        Returns
        -------
        GPIO PWM
            instanse for GPIO PWM
        """
        return self._PWM_LED_green

    @property
    def PWM_LED_switch(self):
        """PWM instanse for switch LED

        Returns
        -------
        GPIO PWM
            instanse for GPIO PWM
        """
        return self._PWM_LED_switch

    @property
    def PWM_servo(self):
        """PWM instanse for servomotor

        Returns
        -------
        GPIO PWM
            instanse for GPIO PWM
        """
        return self._PWM_servo

    @property
    def locked(self):
        """key status

        Returns
        -------
        bool
            key's status (True:locked, False: unlocked)
        """
        return self._unlocked

    @locked.setter
    def locked(self, value):
        """key status

        Parameters
        ----------
        value : bool
            If true, the key is locked now, otherwise unlocked
        """
        if not isinstance(value, bool):
            raise ValueError("locked must be a bool value")
        self._locked = value

    def lock(self):
        """Excute Lock sequence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
        """
        self.PWM_LED_green.ChangeDutyCycle(0)  # switch green LED off
        self.PWM_LED_red.ChangeDutyCycle(50)  # blink red LED (Duty ratio 50%)
        self.buzzer(iteration=2, dt=0.1, interval=0.1)  # sound buzzer

        # control servomotor
        self.PWM_servo.ChangeDutyCycle(7.5)  # positioning
        time.sleep(0.3)
        self.PWM_servo.ChangeDutyCycle(2.5)  # rotate 90 deg
        time.sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(7.5)  # rotate 0 deg
        time.sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(0)  # down to 0 signal

        self.PWM_LED_red.start(100)  # switch red LED on

        # set lock status
        self.locked = True

    def unlock(self):
        """Excute unlock sequence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
        """
        self.PWM_LED_red.ChangeDutyCycle(0)  # switch red LED off
        self.PWM_LED_green.ChangeDutyCycle(50)  # blink green LED (Duty ratio 50%)
        self.buzzer(iteration=3, dt=0.1, interval=0.05)  # sound buzzer

        # control servomotor
        self.PWM_servo.ChangeDutyCycle(7.5)  # positioning
        time.sleep(0.3)
        self.PWM_servo.ChangeDutyCycle(12.5)  # rotate -90 deg
        time.sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(7.5)  # rotate 0 deg
        time.sleep(0.5)
        self.PWM_servo.ChangeDutyCycle(0)  # down to 0 signal

        self.PWM_LED_green.start(100)  # switch green LED on

        # set lock status
        self.locked = False

    def buzzer(self, iteration=3, dt=0.1, interval=0.05):
        """sound buzzer repeatedly

        Parameters
        ----------
        iteration : int
            the number of buzzer cycles
        dt : double
            duration of beep [sec]
        interval : double
            beep interval [sec]
        """
        for n in range(iteration):
            time.sleep(interval)
            GPIO.output(self.pin_buzzer, True)
            time.sleep(dt)
            GPIO.output(self.pin_buzzer, False)

    def _check_pin_overlap(self):
        """check if pin number overlapes with others
        """
        pass
