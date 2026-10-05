from tests.base import ApiCase


class TestProducts(ApiCase):
    def test_list_seeded(self):
        code, data = self.api("GET", "/api/products")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(data), 3)
        titles = [p["title"] for p in data]
        self.assertIn("Мышь", titles)

    def test_get_one(self):
        code, data = self.api("GET", "/api/products/1")
        self.assertEqual(code, 200)
        self.assertEqual(data["id"], 1)
        self.assertIn("price", data)

    def test_get_missing(self):
        code, _ = self.api("GET", "/api/products/999999")
        self.assertEqual(code, 404)

    def test_create_ok_and_db(self):
        code, data = self.auth("POST", "/api/products", {"title": "Монитор", "price": 18990})
        self.assertEqual(code, 201)
        con = self.db()
        row = con.execute("SELECT * FROM products WHERE id=?", (data["id"],)).fetchone()
        con.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Монитор")

    def test_create_no_auth(self):
        code, _ = self.api("POST", "/api/products", {"title": "X", "price": 10})
        self.assertEqual(code, 401)

    def test_create_empty_title(self):
        code, data = self.auth("POST", "/api/products", {"title": "   ", "price": 10})
        self.assertEqual(code, 400)
        self.assertIn("error", data)

    def test_create_bad_price(self):
        for bad in (0, -5, "free", None):
            code, _ = self.auth("POST", "/api/products", {"title": "T", "price": bad})
            self.assertEqual(code, 400, bad)

    def test_update_ok(self):
        _, created = self.auth("POST", "/api/products", {"title": "Часы", "price": 5000})
        code, _ = self.auth("PUT", f"/api/products/{created['id']}", {"price": 4500})
        self.assertEqual(code, 200)
        code, data = self.api("GET", f"/api/products/{created['id']}")
        self.assertEqual(data["price"], 4500)

    def test_update_missing(self):
        code, _ = self.auth("PUT", "/api/products/999999", {"price": 10})
        self.assertEqual(code, 404)

    def test_delete_ok(self):
        _, created = self.auth("POST", "/api/products", {"title": "Удалить", "price": 100})
        code, _ = self.auth("DELETE", f"/api/products/{created['id']}")
        self.assertEqual(code, 200)
        code, _ = self.api("GET", f"/api/products/{created['id']}")
        self.assertEqual(code, 404)

    def test_delete_missing(self):
        code, _ = self.auth("DELETE", "/api/products/999999")
        self.assertEqual(code, 404)
