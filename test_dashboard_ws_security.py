import unittest

from dashboard.ws_utils import WebSocketDisconnect, is_same_origin, ws_session


class _ForeignWebSocket:
    class _URL:
        scheme = "ws"

    url = _URL()
    headers = {"origin": "https://attacker.example", "host": "localhost:8000"}

    def __init__(self):
        self.accepted = False
        self.closed_with = None

    async def accept(self):
        self.accepted = True

    async def close(self, code=None):
        self.closed_with = code


class SameOriginTests(unittest.TestCase):
    def test_rejects_foreign_origin(self):
        self.assertFalse(is_same_origin("https://attacker.example", "localhost:8000", "ws"))

    def test_accepts_matching_origin(self):
        self.assertTrue(is_same_origin("http://localhost:8000", "localhost:8000", "ws"))

    def test_foreign_websocket_is_closed_before_accepting(self):
        import asyncio
        websocket = _ForeignWebSocket()

        async def attempt():
            async with ws_session(websocket):
                self.fail("foreign socket should never enter its route")

        with self.assertRaises(WebSocketDisconnect):
            asyncio.run(attempt())
        self.assertFalse(websocket.accepted)
        self.assertEqual(websocket.closed_with, 1008)


if __name__ == "__main__":
    unittest.main()
