import unittest

from dashboard.auth import is_secure_request, remote_binding_has_https_origin


class DashboardTlsTests(unittest.TestCase):
    def test_remote_binding_requires_an_https_public_origin(self):
        self.assertFalse(remote_binding_has_https_origin("0.0.0.0", ""))
        self.assertFalse(remote_binding_has_https_origin("0.0.0.0", "http://dashboard.example"))
        self.assertTrue(remote_binding_has_https_origin("0.0.0.0", "https://dashboard.example"))

    def test_remote_cleartext_request_is_rejected(self):
        self.assertFalse(is_secure_request("203.0.113.7", "http", "https://dashboard.example"))

    def test_loopback_http_remains_allowed_without_public_origin(self):
        self.assertTrue(is_secure_request("127.0.0.1", "http", ""))


if __name__ == "__main__":
    unittest.main()
