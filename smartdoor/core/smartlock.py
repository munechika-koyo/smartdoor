import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)  # PIN number is used, not GPIO


class SmartLock:
    """ SmartLock class
    This is used to initiate and control raspi GPIO pins, PWM (LED, servomotor), etc.

    PWM instance methods is as follows:
    >>> p = (some PWM instance properties)
    >>> p.start(dc)  # Start PWM, dc: duty cycle (0.0 <= dc <= 100.0)
    >>> p.ChangeFrequency(freq)  # Change Frequency, freq:new frequency [Hz]
    >>> p.ChangeDutyCycle(dc)  # Change Duty Cylcle, (0.0 <= dc <= 100.0)
    >>> p.stop()  # Stop PWM

    Parameters
    ----------
    pins : dict
        pin assignment map
        The following key must be included:
        - switch: input signal from switch
        - LED_red : output signal to red LED
        - LED_green : output signal to green LED
        - LED_switch : output signal to switch LED
        - buzzer : output signal to buzzer
        - servo : output signal to servomotor

    Attributes
    ----------
    PWM_LED_red : :obj:`GPIO.PWM`
        Pulse Width Modulation instance for red LED
    PWM_LED_green : :obj:`GPIO.PWM`
        Pulse Width Modulation instance for green LED
    PWM_LED_switch : :obj:`GPIO.PWM`
        Pulse Width Modulation instance for switch LED
    PWM_servo : :obj:`GPIO.PWM`
        Pulse Width Modulation instance for servomotor

    methods
    -------
    lock()
        excute lock seaquence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
    unlock()
        excute unlock seaquence
        (LED Blinking -> buzzer sounded -> servomotor moving -> LED lighting)
    """

    def __init__(self, pins) -> None:
        # confirm pin assignment
        self.pins = pins

        # initialize pin setup
        GPIO.setup(self.pins["switch"], GPIO.IN)
        GPIO.setup(self.pins["LED_red"], GPIO.OUT)
        GPIO.setup(self.pins["LED_green"], GPIO.OUT)
        GPIO.setup(self.pins["LED_switch"], GPIO.OUT)
        GPIO.setup(self.pins["buzzer"], GPIO.OUT)
        GPIO.setup(self.pins["servo"], GPIO.OUT)

        # initialize PWM objects
        self._PWM_LED_red = GPIO.PWM(self.pins["LED_red"], 5)  # 5Hz PWM
        self._PWM_LED_green = GPIO.PWM(self.pins["LED_green"], 5)
        self._PWM_LED_switch = GPIO.PWM(self.pins["LED_switch"], 5)
        self._PWM_servo = GPIO.PWM(self.pins["servo"], 50)  # 50Hz PWM
        self._PWM_buzzer = GPIO.PWM(self.pins["buzzer"], 2300)  # 880Hz

    @property
    def pins(self):
        """
        dict: pins asssignment map
        """
        return self._pins

    @pins.setter
    def pins(self, value):
        if not isinstance(value, dict):
            raise TypeError("pins must be dict type.")

        self._pins = value

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
    def PWM_buzzer(self):
        """PWM instanse for buzzer

        Returns
        -------
        GPIO PWM
            instanse for GPIO PWM
        """
        return self._PWM_buzzer

    @property
    def locked(self):
        """key status

        Returns
        -------
        bool
            key's status (True:locked, False: unlocked)
        """
        return self._locked

    @locked.setter
    def locked(self, value):
        """key status

        Parameters
        ----------
        value : bool
            If true, the key is locked now, otherwise unlocked
        """
        if not isinstance(value, bool):
            raise TypeError("locked must be a bool value")
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
            self.PWM_buzzer.ChangeDutyCycle(50)
            time.sleep(dt)
            self.PWM_buzzer.ChangeDutyCycle(0)

    def _check_pin_overlap(self):
        """check if pin number overlapes with others
        """
        # pin numbers
        pin_numbers = [
            num for num in self.pins.values()
        ]

        for pin in pin_numbers:
            if pin_numbers.count(pin) > 1:
                raise Exception("detect overlaped pin assignment!")

    def clean(self):
        """clean PWM module and GPIO sequentially
        """
        self.PWM_LED_green.stop()
        self.PWM_LED_red.stop()
        self.PWM_LED_switch.stop()
        self.PWM_servo.stop()
        self.PWM_buzzer.stop()
        GPIO.cleanup()
