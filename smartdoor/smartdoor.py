"""This module provides a main class of SmartDoor system."""
from __future__ import annotations

from binascii import hexlify
from collections import deque
from datetime import datetime
from logging import getLogger
from pathlib import Path
from time import sleep

import requests
from nfc import ContactlessFrontend
from nfc.tag import Tag
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from .core import AuthIDm, SmartLock

# set invisible of https secure warning
disable_warnings(InsecureRequestWarning)

module_logger = getLogger(__name__)


class SmartDoor(SmartLock):
    """Smart Door system class.

    This class has some main fetures of door lock/unlock seaquence, reading/authenticate NFC's IDm,
    and post to IFTTT for notification.

    The user-specific configuration file (`~/.config/smartdoor.toml`) is loaded automatically.
    """

    # define class logger
    logger = getLogger("main").getChild("SmartDoor")

    def __init__(self) -> None:
        # Load default configuration file
        with open(Path(__file__).parent / "default_config.toml", "rb") as file:
            config = tomllib.load(file)

        # Load user-specific configuration file if exists
        config_path = Path.home() / ".config" / "smartdoor.toml"
        if config_path.exists():
            with config_path.open("rb") as file:
                config.update(tomllib.load(file))
                self.logger.debug(f"Loaded user-specific configuration file: {config_path}")

        # === Initialization ==================================================
        # IFTTT
        self._urls: dict[str, str] = {}
        self.urls = config["IFTTT_URLs"]
        self._post_queue: deque = deque()

        # IDm authentication class
        self._auth = AuthIDm(config["auth_url"], config["room"])

        # NFC reader
        self._clf = ContactlessFrontend("usb")

        # room name
        self._room = config["room"]

        # inheritance
        super().__init__(config["pins"])

    @property
    def urls(self) -> dict[str, str]:
        """URL map to post to IFTTT.

        key is event name, value is URL string.
        """
        return self._urls

    @urls.setter
    def urls(self, value):
        if not isinstance(value, dict):
            raise TypeError(f"Invalid type of urls: {type(value)}")

        for key, url in value.items():
            if not isinstance(key, str):
                raise TypeError(f"Invalid type of key: {type(key)}")
            if not isinstance(url, str):
                raise TypeError(f"Invalid type of url: {type(url)}")
            self._urls[key] = url

    @property
    def post_queue(self) -> deque:
        """Queue to store values to post them to IFTTT."""
        return self._post_queue

    @property
    def clf(self) -> ContactlessFrontend:
        """Nfcpy's Contactless Frontend class instance."""
        return self._clf

    @property
    def auth(self) -> AuthIDm:
        """Instance of AuthIDm class."""
        return self._auth

    def wait_for_touched(self) -> None | bool | Tag:
        """Wait for the NFC card to be touched.

        Returns
        -------
        None | bool | obj:`nfc.tag.Tag`
            If the button is pushed, returns None.
            If the KeyboadInterrupt is detected, returns False.
            otherwise, returns the instance of nfcpy's Tag class.
        """
        rdwr_options = {
            "targets": ["212F"],  # detect only Felica
            "on-connect": lambda tag: False,
            "iterations": 5,
            "interval": 0.5,
        }
        tag = self.clf.connect(rdwr=rdwr_options, terminate=self.button.is_pushed)

        return tag

    def authenticate(self, tag: Tag) -> str | None:
        """Authenticate the approved user.

        This method authenticates the user by the IDm of the NFC card.

        Parameters
        ----------
        tag
            the instance of nfcpy's Tag class

        Returns
        -------
        str | None
            If the user is approved, returns the user name.
        """
        # turn on both red and green LEDs
        if self.locked:
            self.led_green.on()
        else:
            self.led_red.on()

        # extract idm
        idm = hexlify(tag.idm).decode("utf-8")

        self.logger.debug(f"idm: {idm} is detected.")

        # authentication
        name = self._auth.authenticate(idm)

        return name

    def post_ifttt(self, user: str = "test", action: str = "LOCK") -> None:
        """Post the info to IFTTT.

        This method posts the info:``{"value1": data, "value2": user, "value3": action}``
        in a json format to IFTTT urls.
        The action means the smartdoor action like a "LOCK", "UNLOCK", etc.

        If the post is failed, the data is cached into a queue and try to post again.

        Parameters
        ----------
        user
            user name, by default "test"
        action
            smartdoor action like "LOCK", "UNLOCK", etc, by default "LOCK"
        """
        # get current datetime
        date_now = datetime.now()
        date_str = date_now.strftime(r"%Y/%m/%d %H:%M:%S")

        # cache post values into a queue
        values = {"value1": date_str, "value2": user, "value3": action}
        self.post_queue.append(values)

        # post to IFTTT in 3 seconds connect timeout and 7.5 seconds read timeout
        try:
            while self.post_queue:
                data = self.post_queue.popleft()

                for event, url in self.urls.items():
                    res = requests.post(url, json=data, timeout=(3.0, 7.5))

                    if res.status_code == 200:
                        self.logger.debug(f"IFTTT post is completed: {event}")
                    else:
                        self.logger.error(
                            f"IFTTT post is failed (code: {res.status_code}): {event}"
                        )
                        self._post_queue.appendleft(data)
                        break

            self.logger.info("IFTTT post is completed.")

        except Exception:
            self.logger.exception("IFTTT post is failed.")
            self._post_queue.appendleft(data)

    def door_sequence(self, user: str = "test") -> None:
        """Door sequence.

        If the door is locked, :obj:`.unlock` method is excuted.
        Otherwise, :obj:`.lock` method is excuted.
        After that, the info is posted to IFTTT by :obj:`.post_ifttt` method.

        Parameters
        ----------
        user
            user name controlling the door, by default "test"
        """
        if self.locked:
            self.unlock()
            action = "UNLOCK"
            self.logger.info(f"unlocked by {user}")
        else:
            self.lock()
            action = "LOCK"
            self.logger.info(f"locked by {user}")

        # post to IFTTT
        self.post_ifttt(user=user, action=action)

    def warning_sequence(self) -> None:
        """Warning sequence when an unauthorized user touched the reader."""
        # Blink red LED and sound buzzer
        self.led_green.off()
        self.led_red.blink(on_time=0.1, off_time=0.1)
        self.buzzer.beep(iteration=2, dt=0.5, interval=0.1)

        # log
        self.logger.info("unauthorized user touched the reader")

        # post to IFTTT
        self.post_ifttt(user="unauthorized user", action="INVALID TOUCH")

        # restore LED
        if self.locked:
            self.led_red.on()
        else:
            self.led_red.off()
            self.led_green.on()

    def error_sequence(self, duration: float = 2) -> None:
        """Error sequence when an program error occurred.

        The sequence is as follows:
        - Blink all LED
        - Sound buzzer for `duration` seconds
        - After that, turn off all LED and buzzer

        Parameters
        ----------
        duration
            duration of the error sequence, by default 2 sec
        """
        # Blink all LED
        self.led_red.blink(on_time=0.1, off_time=0.1)
        self.led_green.blink(on_time=0.1, off_time=0.1)

        # sound buzzer
        self.buzzer.on()
        sleep(duration)

        # Off all LED and buzzer
        self.buzzer.off()
        self.led_red.off()
        self.led_green.off()

    def close(self) -> None:
        """Close the smartdoor system."""
        try:
            self.clf.close()  # close nfc contactlessfrontend instance
            self._auth.close()  # close authentication session
            self.logger.info("smartdoor system is closed.")
        except Exception:
            self.logger.exception("failed to close smartdoor system.")
