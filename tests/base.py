import http.client
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from api.app import make_server

port = 8071


class ApiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # своя база на класс, кладем на A
        tmp = Path(os.environ.get("SHOP_TMP", r"A:\TEMP"))
        tmp.mkdir(parents=True, exist_ok=True)
        fd, db = tempfile.mkstemp(suffix=".db", dir=str(tmp))
        os.close(fd)
        cls._db = db
        os.environ["SHOP_DB"] = db
        cls.server = make_server(port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        code, data = cls.api("POST", "/api/login", {"login": "admin", "password": "1234"})
        assert code == 200, data
        cls.token = data["token"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()
        try:
            os.remove(cls._db)
        except OSError:
            pass

    @staticmethod
    def api(method, path, body=None, token=None, raw=None):
        # вызов апи, возвр. (статус, json)
        con = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        headers = {}
        payload = raw if raw is not None else (json.dumps(body) if body is not None else None)
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        con.request(method, path, body=payload, headers=headers)
        resp = con.getresponse()
        try:
            data = json.loads(resp.read().decode("utf-8") or "null")
        except Exception:
            data = None
        con.close()
        return resp.status, data

    def auth(self, method, path, body=None):
        return self.api(method, path, body, self.token)

    def db(self):
        # прямое чтение базы для сверки
        con = sqlite3.connect(os.environ["SHOP_DB"])
        con.row_factory = sqlite3.Row
        return con
