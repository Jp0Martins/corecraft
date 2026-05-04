# rpc.py
import requests
import json
from config import RPC_URL, COOKIE_FILE

class BitcoinRPC:
    def __init__(self, url=RPC_URL, cookie_file=COOKIE_FILE):
        self.url = url
        self.cookie_file = cookie_file

    def _read_cookie(self):
        with open(self.cookie_file, "r") as f:
            cookie = f.read().strip()
        user, password = cookie.split(":", 1)
        return (user, password)

    def call(self, method, params=[], wallet=None):
        url = self.url
        if wallet:
            url = f"{self.url}/wallet/{wallet}"

        payload = {
            "jsonrpc": "1.0",
            "id": "corecraft",
            "method": method,
            "params": params
        }

        auth = self._read_cookie()
        response = requests.post(url, auth=auth, data=json.dumps(payload))
        result = response.json()

        if result.get("error"):
            raise Exception(result["error"])

        return result["result"]
