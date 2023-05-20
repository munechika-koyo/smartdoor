"""This module provides IDm authentication functions communicating with database through web api."""
from __future__ import annotations

import sys
from logging import getLogger

from requests import Request, Session

module_logger = getLogger(__name__)


class AuthIDm:
    """Authentication for IDm using web api.

    Parameters
    ----------
    url
        URL address to post IDm data
    room
        name of room to authenticate, e.g. "423"
    timeout
        session timeout to connect to the database, by default 10 sec
    """

    logger = getLogger("main").getChild("AuthIDm")

    def __init__(self, url: str, room: str, timeout: float = 10) -> None:
        try:
            # get CSRF token in cookies
            session = Session()
            session.get(url, timeout=timeout, verify=False)

            # instantiate request object
            headers = {
                "Content-type": "application/json",
                "X-CSRFToken": session.cookies["csrftoken"],
            }
            req = Request("POST", url, headers=headers)

        except Exception as e:
            self.logger.error(f"cannot establish the connection to {url}")
            self.logger.debug(f"{type(e)}: {e}")
            sys.exit(1)

        # save variables as properties
        self._session = session
        self._request = req
        self._room = room

    @property
    def session(self) -> Session:
        """Session object."""
        return self._session

    @property
    def request(self) -> Request:
        """Request object."""
        return self._request

    @property
    def room(self) -> str:
        """Room name."""
        return self._room

    def authenticate(self, idm: str, timeout: float = 5) -> str | None:
        """IDm authentication method.

        If the given idm is validated, returns user name which is registered in database.
        Otherwise returns None.

        Parameters
        ----------
        idm
            Hexadecimal IDm converted to string
        timeout
            post requesting timeout to the database, by default 5 sec

        Returns
        -------
        str | None
            username which is registered in database, if not, retuning None.
        """
        if not isinstance(idm, str):
            self.logger.error("idm must be string containing 16 hexadecimal digits.")
            return None

        self._request.json = {"idm": idm}

        # request preparation
        prepared_req = self.session.prepare_request(self._request)
        try:
            response = self._session.send(prepared_req, timeout=timeout, verify=False)
            data = response.json()

            if data["auth"] == "valid":
                if data[f"allow_{self._room}"]:
                    return data["name"]
            return None

        except Exception as e:
            self.logger.error(f"{type(e)}: {e}")
            return None

    def close(self):
        """Close session."""
        self.logger.debug("close session")
        self._session.close()


# for debug
if __name__ == "__main__":
    url = "http://localhost:8000/authenticate/"
    room = "423"
    auth = AuthIDm(url, room)

    print(auth.authenticate("013BDD2FEE1FC80D"))
    auth.close()
