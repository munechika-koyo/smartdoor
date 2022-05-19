import os
import datetime
import requests
import RPi.GPIO as GPIO
from binascii import hexlify
from nfc import ContactlessFrontend
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
        self.URLs = conf["IFTTT_URLs"]
        self.post_list = []

        # instantiate IDm authentication class
        self._auth = AuthIDm(conf["database"], conf["room"])

        # NFC reader
        self._clf = ContactlessFrontend("usb")  # NFC reader

        self._room = conf["room"]  # room name

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
    def URLs(self):
        """
        list: URL lists to post to IFTTT
        """
        return self._URLs

    @URLs.setter
    def URLs(self, value):
        if not isinstance(value, list):
            raise TypeError("URLs must be list containg URL strings")
        self._URLs = value

    @property
    def post_list(self):
        """
        list: dict values to post to IFTTT
        """
        return self._post_list

    @post_list.setter
    def post_list(self, value):
        if not isinstance(value, list):
            raise TypeError("post_list must be list.")
        self._post_list = value

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
        # extract idm
        idm = hexlify(tag.idm).decode("utf-8")

        self.log.info(f"idm: {idm} is detected")

        return self._auth.authenticate(idm)

    def post_IFTTT(self, user="test", action="test"):
        """post to IFTTT URL
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
        values = {"value1": date_str, "value2": user, "value3": action}
        # store post values temporaly
        self.post_list.append(values)
        # post values to URLs in 3.5 sec
        try:
            for URL in self.URLs:
                for value in self.post_list:
                    requests.post(URL, json=value, timeout=5.0)

            # clear all components in list if successfully sending it.
            self.post_list.clear()
            self.log.info("IFTTT POST successed")

        except Exception as e:  # in case of timeout
            self.log.error(e)

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
        self.log.info("excute closing sequence")
        self.clf.close()  # close nfc contactlessfrontend instance
        self._auth.close()  # close database session
        self.clean()  # cleanup of raspi GPIO
