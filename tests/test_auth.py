from tests.base import ApiCase


class TestAuth(ApiCase):
    def test_login_ok(self):
        code, data = self.api("POST", "/api/login", {"login": "admin", "password": "1234"})
        self.assertEqual(code, 200)
        self.assertTrue(data["token"])

    def test_login_bad_password(self):
        code, data = self.api("POST", "/api/login", {"login": "admin", "password": "nope"})
        self.assertEqual(code, 401)
        self.assertIn("error", data)

    def test_login_unknown_user(self):
        code, _ = self.api("POST", "/api/login", {"login": "ghost", "password": "1234"})
        self.assertEqual(code, 401)

    def test_me_with_token(self):
        code, data = self.auth("GET", "/api/me")
        self.assertEqual(code, 200)
        self.assertEqual(data["login"], "admin")

    def test_me_without_token(self):
        code, _ = self.api("GET", "/api/me")
        self.assertEqual(code, 401)

    def test_me_bad_token(self):
        code, _ = self.api("GET", "/api/me", token="deadbeef")
        self.assertEqual(code, 401)
