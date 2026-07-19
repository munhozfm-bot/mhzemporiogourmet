import importlib
import os
import tempfile
import unittest


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = os.path.join(self.temp_dir.name, "test.db")
        os.environ["SECRET_KEY"] = "test-secret-key"

        import app as app_module

        self.app_module = importlib.reload(app_module)
        self.app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def login(self):
        return self.client.post(
            "/login",
            data={"email": "admin@mhz.local", "password": "MHZ@2026"},
            follow_redirects=True,
        )

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_login_and_products_page(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dashboard executivo", response.get_data(as_text=True))

        response = self.client.get("/products")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Baggio", response.get_data(as_text=True))

    def test_csrf_token_is_rendered_as_hidden_input(self):
        login_response = self.client.get("/login")
        self.assertEqual(login_response.status_code, 200)
        self.assertIn('<input type="hidden" name="csrf_token"', login_response.get_data(as_text=True))

        self.login()
        product_form_response = self.client.get("/products/new")
        self.assertEqual(product_form_response.status_code, 200)
        self.assertIn('<input type="hidden" name="csrf_token"', product_form_response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
