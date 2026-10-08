import unittest

from utils.tg_utils import code_delivery_label


class LoginDeliveryTests(unittest.TestCase):
    def test_labels_telegram_app_delivery(self):
        sent = type("Sent", (), {"type": type("SentCodeTypeApp", (), {})()})()
        self.assertEqual(code_delivery_label(sent), "the Telegram app on another logged-in device")

    def test_labels_sms_delivery(self):
        sent = type("Sent", (), {"type": type("SentCodeTypeSms", (), {})()})()
        self.assertEqual(code_delivery_label(sent), "SMS")


if __name__ == "__main__":
    unittest.main()
