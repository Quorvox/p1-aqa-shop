import json
import secrets
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from api.db import connect, init_db

tokens = {}  # токен -> логин


class Handler(BaseHTTPRequestHandler):
    server_version = "Shop/1.0"

    def _body(self):
        # читаем json, при битом возвращ. None
        ln = int(self.headers.get("Content-Length", 0))
        if not ln:
            return {}
        try:
            return json.loads(self.rfile.read(ln).decode("utf-8"))
        except Exception:
            return None

    def _send(self, code, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _user(self):
        # логин по Bearer-токену, иначе None
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        return tokens.get(auth[7:])

    def _product_id(self, path):
        try:
            return int(path.rsplit("/", 1)[1])
        except ValueError:
            return None

    def log_message(self, *a):
        pass  # тихо для тестового вывода

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/health":
            return self._send(200, {"ok": True})
        if path == "/api/products":
            con = connect()
            rows = [dict(r) for r in con.execute("SELECT * FROM products ORDER BY id")]
            con.close()
            return self._send(200, rows)
        if path.startswith("/api/products/"):
            pid = self._product_id(path)
            con = connect()
            row = con.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone() if pid else None
            con.close()
            if not row:
                return self._send(404, {"error": "not found"})
            return self._send(200, dict(row))
        if path == "/api/me":
            login = self._user()
            if not login:
                return self._send(401, {"error": "need token"})
            return self._send(200, {"login": login})
        if path == "/api/orders":
            login = self._user()
            if not login:
                return self._send(401, {"error": "need token"})
            con = connect()
            rows = [dict(r) for r in con.execute(
                "SELECT id,total,items,created FROM orders WHERE login=? ORDER BY id", (login,))]
            con.close()
            return self._send(200, rows)
        self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        data = self._body()
        if data is None:
            return self._send(400, {"error": "bad json"})
        if path == "/api/login":
            con = connect()
            row = con.execute("SELECT * FROM users WHERE login=? AND password=?",
                              (data.get("login"), data.get("password"))).fetchone()
            con.close()
            if not row:
                return self._send(401, {"error": "bad credentials"})
            tok = secrets.token_hex(16)
            tokens[tok] = data["login"]
            return self._send(200, {"token": tok})
        login = self._user()
        if not login:
            return self._send(401, {"error": "need token"})
        if path == "/api/products":
            title = (data.get("title") or "").strip()
            price = data.get("price")
            if not title:
                return self._send(400, {"error": "title required"})
            if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
                return self._send(400, {"error": "price must be > 0"})
            con = connect()
            cur = con.execute("INSERT INTO products(title,price) VALUES(?,?)", (title, price))
            con.commit()
            pid = cur.lastrowid
            con.close()
            return self._send(201, {"id": pid, "title": title, "price": price})
        if path == "/api/orders":
            items = data.get("items")
            if not isinstance(items, list) or not items:
                return self._send(400, {"error": "items required"})
            con = connect()
            total = 0
            norm = []
            for it in items:
                qty = it.get("qty", 0)
                if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                    con.close()
                    return self._send(400, {"error": "qty must be int > 0"})
                row = con.execute("SELECT * FROM products WHERE id=?", (it.get("id"),)).fetchone()
                if not row:
                    con.close()
                    return self._send(404, {"error": f"product {it.get('id')} not found"})
                total += row["price"] * qty
                norm.append({"id": row["id"], "qty": qty, "price": row["price"]})
            cur = con.execute("INSERT INTO orders(login,total,items,created) VALUES(?,?,?,?)",
                              (login, total, json.dumps(norm, ensure_ascii=False),
                               datetime.now().isoformat(timespec="seconds")))
            con.commit()
            oid = cur.lastrowid
            con.close()
            return self._send(201, {"id": oid, "total": total})
        self._send(404, {"error": "not found"})

    def do_PUT(self):
        path = urllib.parse.urlparse(self.path).path
        if not path.startswith("/api/products/"):
            return self._send(404, {"error": "not found"})
        login = self._user()
        if not login:
            return self._send(401, {"error": "need token"})
        data = self._body()
        if data is None:
            return self._send(400, {"error": "bad json"})
        pid = self._product_id(path)
        con = connect()
        row = con.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone() if pid else None
        if not row:
            con.close()
            return self._send(404, {"error": "not found"})
        title = data.get("title", row["title"])
        price = data.get("price", row["price"])
        if isinstance(title, str):
            title = title.strip()
        if not title or not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
            con.close()
            return self._send(400, {"error": "bad title/price"})
        con.execute("UPDATE products SET title=?, price=? WHERE id=?", (title, price, pid))
        con.commit()
        con.close()
        return self._send(200, {"ok": True})

    def do_DELETE(self):
        path = urllib.parse.urlparse(self.path).path
        if not path.startswith("/api/products/"):
            return self._send(404, {"error": "not found"})
        login = self._user()
        if not login:
            return self._send(401, {"error": "need token"})
        pid = self._product_id(path)
        con = connect()
        cur = con.execute("DELETE FROM products WHERE id=?", (pid,))
        con.commit()
        gone = cur.rowcount
        con.close()
        if not gone:
            return self._send(404, {"error": "not found"})
        return self._send(200, {"ok": True})


def make_server(port=8071):
    init_db()
    return HTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    init_db()
    print("shop api on http://127.0.0.1:8071")
    HTTPServer(("127.0.0.1", 8071), Handler).serve_forever()
