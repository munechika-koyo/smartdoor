import os
import datetime
import requests
import RPi.GPIO as GPIO
from binascii import hexlify
from nfc import ContactlessFrontend
from collections import deque
from yaml import safe_load
from logging import Logger, getLogger

from .core import SmartLock
from .core import AuthIDm


class SmartDoor(SmartLock):
    """Smart Door system class
    This class has some fetures of door lock/unlock seaquence, reading NFC,


    Parameters
    ----------
    path : str
        path to configure file formated by yaml where several configuration is written.
    log : :obj:`.logging.RootLogger`
        logging instance
    """
    def __init__(self, path=None, log=None) -> None:
        # Load configration yaml file
        if path is None:
            raise ValueError("path must be the name to the appropriate configuration yaml file.")
        _, ext = os.path.splitext(os.path.basename(path))
        if ext != ".yaml":
            raise ValueError("configuration file must be formated by yaml.")
        with open(path, "r") as f:
            conf = safe_load(f)

        # === Initialization ==================================================
        # Logger
        self.log = log or getLogger(__name__)

        # IFTTT
        self.urls = conf["IFTTT_URLs"]
        self._post_queue = deque()

        # instantiate IDm authentication class
        self._auth = AuthIDm(conf["database"], conf["room"])

        # NFC reader
        self._clf = ContactlessFrontend("usb")

        # room name
        self._room = conf["room"]

        # inheritance
        super().__init__(conf["pin"])

    @property
    def log(self):
        """
        :obj:`.logging.RootLogger`: instance of Logger object
        """
        return self._log

    @log.setter
    def log(self, value):
        if not isinstance(value, Logger):
            raise TypeError("log must be an instance of logging.Logger")
        self._log = value

    @property
    def urls(self):
        """
        list: URL lists to post to IFTTT
        """
        return self._urls

    @urls.setter
    def urls(self, value):
        if not isinstance(value, list):
            raise TypeError("urls must be list containg URL strings")
        self._urls = value

    @property
    def post_queue(self):
        """
        :obj:~`collections.deque`: queue to store values to post them to IFTTT
        """
        return self._post_queue

    @property
    def clf(self):
        """
        :obj:`.nfc.clf.ContactlessFrontend`: nfcpy's Contactless Frontend class instance
        """
        return self._clf

    @property
    def auth(self):
        """
        :obj:`.AuthIDm`: instance of AuthIDm class
        """
        return self._auth

    def wait_ICcard_touched(self):
        """waiting for IC card touched
        If the button is pushed, None is returned.
        If the KeyboadInterrupt is detected, False is returned.

        Returns
        -------
        tag : :obj:`nfc.tag.Tag`
            the instance of nfcpy's Tag class.
            If the button is pushed, None.
            If the KeyboadInterrupt is detected, False.
        """
        rdwr_options = {
            "targets": ["212F"],  # detect only Felica
            "on-connect": lambda tag: False,
            "iterations": 5,
            "interval": 0.2,
        }
        tag = self.clf.connect(rdwr=rdwr_options, terminate=self._teminate)

        return tag

    def _teminate(self):
        """terminate function for self.clf.connect() method.
        This must return only boolean value.

        Returns
        -------
        bool
            If the button is pushed, True
            Otherwise, False.
        """
        return bool(GPIO.input(self.pins["switch"]))

    def authenticate(self, tag):
        """Authenticate the approved user
        This method checks if the user who touched the IC card reader is allowed
        to control door seaquence.

        Parameters
        ----------
        tag : :obj:`nfc.tag.Tag`
            the instance of nfcpy's Tag class, which is the return value as the ``clf.connect()`` method.

        Returns
        -------
        str
            the user name registerd in database if not, None
        """
        # turn on the both red and green LEDs
        if self.looked:
            self.PWM_LED_green.ChangeDutyCycle(100)
        else:
            self.PWM_LED_red.ChangeDutyCycle(100)

        # extract idm
        idm = hexlify(tag.idm).decode("utf-8")

        self.log.info(f"idm: {idm} is detected")

        # authentication
        name = self._auth.authenticate(idm)

        return name

    def post_IFTTT(self, user="test", action="test"):
        """post values to IFTTT
        This method posts the info about
        {"value1": data, "value2": user, "value3": action}
        as a json format. The action means the smartdoor action like a "LOCK", "UNLOCK", etc.

        Parameters
        ----------
        user : str
            user name, by default "test"
        action : str
            smartdoor action like "LOCK", "UNLOCK", etc, by default "test"
        """
        # get current datetime
        date_now = datetime.datetime.now()
        date_str = date_now.strftime(r"%Y/%m/%d %H:%M:%S")

        # cache values into a queue
        values = {"value1": date_str, "value2": user, "value3": action}
        self.post_queue.append(values)

        # post values to urls in 3.0 sec
        try:
            while self.post_queue:
                data = self.post_queue.popleft()
                for url in self.urls:
                    requests.post(url, json=data, timeout=3.0)

            self.log.info("IFTTT POST successed")

        except TimeoutError as e:  # in case of timeout
            self.log.error(e)
            self._post_queue.appendleft(data)

    def door_sequence(self, user="test"):
        """door sequence
        if door is locked, :obj:`.unlock` method is excuted, otherwise,
        :obj:`.lock` method is excuted.
        Afterwards, :obj:`.post_IFTTT` methods is excuted.

        Parameters
        ----------
        user : str
            user name controling the smartdoor system, by default "test"
        """
        if self.locked:
            self.unlock()
            action = "UNLOCK"
            self.log.info("unlocked by " + user)
        else:
            self.lock()
            action = "LOCK"
            self.log.info("locked by " + user)

        # post IFTTT
        self.post_IFTTT(user=user, action=action)

    def warning_invalid_touch(self):
        """warning sequence when the unauthorized user touches card reader.
        """
        # Blink red LED and sound buzzer
        self.PWM_LED_green.ChangeDutyCycle(0)
        self.PWM_LED_red.ChangeDutyCycle(50)
        self.buzzer(iteration=2, dt=0.5, interval=0.1)
        # log
        self.log.info("invalid touched by an unauthorized user")

        # post warning message
        self.post_IFTTT(user="unauthorized user", action="INVALID TOUCH")

        # set previouse LED setting
        if self.locked:
            self.PWM_LED_red.ChangeDutyCycle(100)
        else:
            self.PWM_LED_green.ChangeDutyCycle(100)
            self.PWM_LED_red.ChangeDutyCycle(0)

    def start(self):
        """start sequence
        put the LED on and off
        start servomotor
        """
        self.log.info("smartdoor system starts")
        if self.locked:
            self.PWM_LED_green.start(0)
            self.PWM_LED_red.start(100)
        else:
            self.PWM_LED_green.start(100)
            self.PWM_LED_red.start(0)

        self.PWM_LED_switch.start(100)
        self.PWM_servo.start(0)

    def close(self):
        """close sequence
        """
        self.log.info("excute closing sequence...")
        self.clf.close()  # close nfc contactlessfrontend instance
        self._auth.close()  # close database session
        self.clean()  # cleanup of raspi GPIO
        self.log.info("smartdoor system normally closed.")
