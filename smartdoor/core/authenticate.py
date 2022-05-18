"""
This module provides authentication tools for IDm with database requests
"""
from requests import Request, Session


class AuthIDm:
    """
    Authentication for IDm with requesting data to database through web api.

    Parameters
    ----------
    url : str
        url address to post IDm data
    room : str
        name of room to authenticate
    timeout : int, optional
        session timeout to connect to the database, by default 10 sec
    """
    def __init__(self, url, room, timeout=10) -> None:

        try:
            # get csrf token in cookies
            session = Session()
            session.get(url, timeout=timeout, verify=False)

            # instantiate request object
            headers = {"Content-type": "application/json", "X-CSRFToken": session.cookies["csrftoken"]}
            req = Request("POST", url, headers=headers)

        except TimeoutError:
            raise TimeoutError(f"cannot establish the connection to {url}")

        # save variables as properties
        self._session = session
        self._request = req
        self._room = room

    @property
    def session(self):
        """
        :obj:`.requests.sessions.Session`: session object
        """
        return self._session

    @property
    def request(self):
        """
        :obj:`.requests.models.Request`: request object
        """
        return self._request

    @property
    def room(self):
        """
        str: room name
        """
        return self._room

    def authenticate(self, idm, timeout=10):
        """
        IDm authentication method
        If the given idm is validated, returns user name which is registered in database.
        Otherwise returns None.

        Parameters
        ----------
        idm : str
            Hexadecimal IDm converted to string
        timeout : int, optional
            post requesting timeout to the database, by default 10 sec

        Returns
        -------
        str or null
            username which is registered in database, if not, retuning None.
        """
        if not isinstance(idm, str):
            raise TypeError("idm must be string containg 16 hexadecimal digits.")

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

        except Exception:
            return None

    def close(self):
        """
        close session
        """
        self._session.close()


# for debug
if __name__ == "__main__":
    url = "http://localhost:8000/authenticate/"
    room = "423"
    auth = AuthIDm(url, room)

    print(auth.authenticate("013BDD2FEE1FC80D"))
    auth.close()
