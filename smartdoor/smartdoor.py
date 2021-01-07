import sqlite3
import RPi.GPIO as GPIO
import time
from nfc import ContactlessFrontend
from yaml import safe_load
import sqlite3

from smartdoor import SmartLock


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
        with open(path, "r") as f:
            conf = safe_load(f)

        # initialize
        self.URLs = conf["IFTTT_URLs"]  # IFTTT
        self._database = sqlite3.connect(conf["database"])  # database
        self._clf = ContactlessFrontend("usb")  # NFC reader

        super().__init__(**conf["pin"])

    @property
    def URLs(self):
        return self._URLs
    @URLs.setter
    def URLs(self, value):
        if not isinstance(value, list):
            raise ValueError("URLs must be list containg URL strings")
        self._URLs = value

    @property
    def clf(self):
        return self._clf

    @property
    def database(self):
        return self._database

    def wait_nfc_touching(self):
        return tag

    def authenticate(self, tag):
        return user

    def door_sequence(self, user):
