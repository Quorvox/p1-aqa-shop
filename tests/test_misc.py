from tests.base import ApiCase


class TestMisc(ApiCase):
    def test_health(self):
        code, data = self.api("GET", "/api/health")
        self.assertEqual(code, 200)
        self.assertTrue(data["ok"])

    def test_unknown_route(self):
        code, data = self.api("GET", "/api/nope")
        self.assertEqual(code, 404)
        self.assertIn("error", data)

    def test_broken_json(self):
        code, data = self.api("POST", "/api/login", raw="{oops")
        self.assertEqual(code, 400)

    def test_products_content_type(self):
        # заголовок именно json с utf-8
        import http.client
        from tests.base import port
        con = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        con.request("GET", "/api/products")
        resp = con.getresponse()
        ctype = resp.getheader("Content-Type")
        con.close()
        self.assertIn("application/json", ctype)
