import asyncio
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dashboard.services import sessions_service as service


class _Client:
    def __init__(self, *args):
        self.disconnected = False

    async def connect(self):
        pass

    async def is_user_authorized(self):
        return True

    async def get_me(self):
        return SimpleNamespace(username="main", first_name="Main", last_name=None, id=1)

    async def disconnect(self):
        self.disconnected = True


class SessionSafetyTests(unittest.TestCase):
    def test_verification_uses_the_shared_session_lock(self):
        entered = []

        @asynccontextmanager
        async def lock(session_name):
            entered.append(session_name)
            yield

        with patch.object(service, "TelegramClient", _Client), patch.object(service, "session_lock", lock):
            asyncio.run(service.check_session("main"))

        self.assertEqual(entered, ["main"])

    def test_expired_flow_disconnects_and_removes_its_temporary_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_name = str(Path(temp_dir) / "temp_login_old")
            Path(f"{temp_name}.session").touch()
            client = _Client()
            service._FLOWS["old"] = service.LoginFlow(
                id="old", client=client, temp_session_name=temp_name, created_at=0,
            )
            asyncio.run(service.cleanup_login_flows(now=601))

            self.assertTrue(client.disconnected)
            self.assertFalse(Path(f"{temp_name}.session").exists())
            self.assertNotIn("old", service._FLOWS)


if __name__ == "__main__":
    unittest.main()
