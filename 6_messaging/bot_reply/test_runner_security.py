import unittest

from runner import is_operator_callback, on_button_callback


class _UnauthorizedEvent:
    sender_id = 200
    data = b"approve:1"

    def __init__(self):
        self.answer_args = None

    async def answer(self, message, alert=False):
        self.answer_args = (message, alert)


class _ForbiddenDatabase:
    def __getattr__(self, name):
        raise AssertionError(f"unauthorized callback reached database method {name}")


class OperatorCallbackTests(unittest.TestCase):
    def test_rejects_a_callback_from_another_telegram_user(self):
        self.assertFalse(is_operator_callback(200, 100))

    def test_accepts_the_configured_operator(self):
        self.assertTrue(is_operator_callback(100, 100))

    def test_unauthorized_callback_cannot_change_a_reply(self):
        event = _UnauthorizedEvent()
        import asyncio
        asyncio.run(on_button_callback(event, _ForbiddenDatabase(), None, 100))
        self.assertEqual(event.answer_args, ("Not authorized.", True))


if __name__ == "__main__":
    unittest.main()
