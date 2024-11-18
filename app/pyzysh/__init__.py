import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import json


class Client:
    def __init__(
        self,
        host,
        username,
        password,
        port=443,
        ssl=True,
        ssl_verify=True,
    ):
        self._host = host
        self._port = port
        self._ssl = ssl
        self._username = username
        self._password = password
        self._disable_ssl_verification = not ssl_verify

        self._session = requests.Session()
        self._session.verify = not self._disable_ssl_verification if self._ssl else True

        self._url = f"http{'s' if self._ssl else ''}://{self._host}:{self._port}"

    def get_csrf_token(self):
        response = self._session.get(f"{self._url}/login")
        if response and response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", {"name": "CSRFToken"})["value"]
            return csrf_token
        return None

    def login(self):
        csrf_token = self.get_csrf_token()
        if not csrf_token:
            print("Failed to retrieve CSRF token")
            return False

        post_data = urlencode(
            {
                "username": self._username,
                "password": self._password,
                "CSRFToken": csrf_token,
            }
        )

        response = self._session.post(
            f"{self._url}/",
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        )

        if response and response.status_code == 302:
            return None

        raise Exception("Failed to login")

    def exec(self, command):
        post_data = urlencode(
            {
                "filter": "js2",
                "cmd": command,
                "write": "0",
            }
        )

        response = self._session.post(
            f"{self._url}/cgi-bin/zysh-cgi",
            data=post_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        if response and response.status_code == 200:
            response_dict = {}
            for line in response.text.split("\n"):
                line = line.strip()  # Remove any leading/trailing whitespace
                if len(line) > 0 and line.startswith("var ") and line.endswith(";"):
                    # Remove prefix and suffix
                    cleaned_line = (
                        line[len("var ") :] if line.startswith("var ") else line
                    )
                    cleaned_line = (
                        cleaned_line[:-1]
                        if cleaned_line.endswith(";")
                        else cleaned_line
                    )
                    # Split into key-value pair
                    if "=" in cleaned_line:
                        key, value = cleaned_line.split("=", 1)
                        response_dict[key.strip()] = value.strip()

            if response_dict["errno0"] == "0":
                return eval(response_dict["zyshdata0"])
            else:
                raise Exception(response_dict["errmsg0"])
