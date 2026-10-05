import json

from tests.base import ApiCase


class TestOrders(ApiCase):
    def test_create_total(self):
        # 1490*2 + 890 = 3870, сверяем расчет
        code, data = self.auth("POST", "/api/orders",
                               {"items": [{"id": 1, "qty": 2}, {"id": 3, "qty": 1}]})
        self.assertEqual(code, 201)
        self.assertEqual(data["total"], 1490 * 2 + 890)

    def test_create_saved_in_db(self):
        _, order = self.auth("POST", "/api/orders", {"items": [{"id": 2, "qty": 1}]})
        con = self.db()
        row = con.execute("SELECT * FROM orders WHERE id=?", (order["id"],)).fetchone()
        con.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["total"], 3990)
        self.assertEqual(json.loads(row["items"])[0]["id"], 2)

    def test_create_bad_product(self):
        code, _ = self.auth("POST", "/api/orders", {"items": [{"id": 999999, "qty": 1}]})
        self.assertEqual(code, 404)

    def test_create_bad_qty(self):
        for bad in (0, -1, "2"):
            code, _ = self.auth("POST", "/api/orders", {"items": [{"id": 1, "qty": bad}]})
            self.assertEqual(code, 400, bad)

    def test_create_empty_items(self):
        code, _ = self.auth("POST", "/api/orders", {"items": []})
        self.assertEqual(code, 400)

    def test_list_orders(self):
        self.auth("POST", "/api/orders", {"items": [{"id": 1, "qty": 1}]})
        code, data = self.auth("GET", "/api/orders")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(data), 1)

    def test_list_no_auth(self):
        code, _ = self.api("GET", "/api/orders")
        self.assertEqual(code, 401)
