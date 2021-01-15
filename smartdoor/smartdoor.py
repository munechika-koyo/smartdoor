import os
import datetime
import sqlite3
import requests
import RPi.GPIO as GPIO
from binascii import hexlify
from nfc import ContactlessFrontend
from yaml import safe_load
from logging import Logger, getLogger

from smartdoor.core import SmartLock


class SmartDoor(SmartLock):
    """Smart Door system class
    This class has some fetures of door lock/unlock seaquence, reading NFC,


    Parameters
    ----------
    path : str
        path to conf.yaml where several configuration is written.
    log : logging object
        logging instance
    """
    def __init__(self, path=None, log=None) -> None:
        # Load configration from conf.yaml
        if path is None:
            raise ValueError("must set the appropriate file path to 'conf.yaml'.")
        filename, ext = os.path.splitext(os.path.basename(path))
        if filename != "conf" or ext != ".yaml":
            raise ValueError("must set the appropriate file path to 'conf.yaml'.")
        with open(path, "r") as f:
            conf = safe_load(f)

        # initialize
        self.log = log or getLogger(__name__)
        self.URLs = conf["IFTTT_URLs"]  # IFTTT
        self._database = sqlite3.connect(conf["database"])  # database
        self._database.row_factory = sqlite3.Row
        self._clf = ContactlessFrontend("usb")  # NFC reader
        self._room = conf["room"]  # room name
        self.post_list = []  # for IFTTT post

        super().__init__(**conf["pin"])  # set pin assignment

    @property
    def log(self):
        """instance of Logger object

        Returns
        -------
        logging.Logger
            logging.Logger class
        """
        return self._log

    @log.setter
    def log(self, value):
        """set the instance of Logger object

        Parameters
        ----------
        value : logging.Logger
            logging.Logger instance
        """
        if not isinstance(value, Logger):
            raise TypeError("log must be an instance of logging.Logger")
        self._log = value

    @property
    def URLs(self):
        """URL lists to post to IFTTT

        Returns
        -------
        list
            list contains URL strings to post to IFTTT
        """
        return self._URLs

    @URLs.setter
    def URLs(self, value):
        """set URL lists to post to IFTTT

        Parameters
        ----------
        value : list
            contains URLs (e.g. ["https://...", "https://..."])
        """
        if not isinstance(value, list):
            raise TypeError("URLs must be list containg URL strings")
        self._URLs = value

    @property
    def post_list(self):
        """list to post to IFTTT
        This is a list containing dicts like
        [{"value1":..., "value2": ..., "value3": ...}, ...],
        to temporaly store such data in case that post requesting is suddenly canceled.

        Returns
        -------
        list
            containg dicts data to post IFTTT
        """
        return self._post_list

    @post_list.setter
    def post_list(self, value):
        """list to post to IFTTT
        This list must contain dicts like
        [{"value1":..., "value2": ..., "value3": ...}, ...],
        to temporaly store such data in case that post requesting is suddenly canceled.

        Parameters
        ----------
        value : list
            containg dicts data to post IFTTT
        """
        if not isinstance(value, list):
            raise TypeError("post_list must be list.")
        self._post_list = value

    @property
    def clf(self):
        """nfcpy's Contactless Frontend class instance
        Contactless Frontend class provides several methods to make it easy to access
        to the contactless functionality.

        Returns
        -------
        nfc.clf.ContactlessFrontend
            instance of Contactless Frontend class
        """
        return self._clf

    @property
    def database(self):
        """database storing user's idms
        This database uses SQlite database system, and the database path
        is configurable only by "conf.yaml"

        Returns
        -------
        sqlite3.Connection
            sqlite3 Connection object
        """
        return self._database

    @property
    def room(self):
        """Room name where smartdoor system is implemeted.
        This property is used when authenticating the authorized user,
        e.g. a certain user is allowd to enter into room "N2_423".
        This property is configurable only by "conf.yaml"

        Returns
        -------
        str
            room name e.g. "N2_423"
        """
        return self._room

    def wait_ICcard_touched(self):
        """waiting for IC card touched
        If the button is pushed, None is returned.
        If the KeyboadInterrupt is detected, False is returned.

        Returns
        -------
        tag : nfc.tag.Tag, None, or False
            the instance of nfcpy's Tag class.
            If the button is pushed, None.
            If the KeyboadInterrupt is detected, False.
        """
        rdwr_options = {"targets": ["212F"],  # detect only Felica
                        "on-connect": lambda tag: False,
                        "iterations": 5,
                        "interval": 0.2}
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
        return bool(GPIO.input(self.pin_switch))

    def authenticate(self, tag):
        """Authenticate the approved user
        This method checks if the user who touched the IC card reader is allowed
        to control door seaquence.

        Parameters
        ----------
        tag : nfc.tag.Tag
            the instance of nfcpy's Tag class, which is the return value as the clf.connect() method.

        Returns
        -------
        str
            the user name registerd in database
        """
        # extract idm
        idm = hexlify(tag.idm).decode("utf-8")

        # search database for the corresponding idm
        cursor = self.database.cursor()
        cursor.execute("SELECT * FROM smartdoor WHERE idm=?", (idm,))
        result = cursor.fetchone()

        # if no one is identified
        if result is None:
            return result
        # if the user is allowed to control the specific room
        elif result["Allow_" + self.room]:
            return result["user"]
        # if the user is not allowed
        else:
            return None

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
        date_str = date_now.strftime("%Y年%m月%d日 %H:%M:%S")
        values = {"value1": date_str,
                  "value2": user,
                  "value3": action}
        # store post values temporaly
        self.post_list.append(values)
        # post values to URLs in 3.5 sec
        try:
            for URL in self.URLs:
                for value in self.post_list:
                    requests.post(URL, json=value, timeout=3.5)  # with 3.5 sec timeout

            # clear all components in list if successfully sending it.
            self.post_list.clear()
            self.log.info("IFTTT POST successed")

        except Exception:  # in case of timeout
            self.log.error("IFTTT POST failed")

    def door_sequence(self, user="test"):
        """door sequence
        if door is locked, self.unlock() method is excuted, otherwise,
        self.lock() method is excuted.
        Afterwards, post_IFTTT() methods is excuted.

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
        self.post_IFTTT(user="許可されていないユーザー", action="INVALID TOUCH")

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
        self.database.close()  # close database
        self.clean()  # cleanup of raspi GPIO
