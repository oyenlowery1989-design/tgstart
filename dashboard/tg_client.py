"""Builds TelegramClient instances using the suite's MAIN_API_ID/API_ID fallback convention."""
import asyncio
import os
from collections import defaultdict
from dotenv import load_dotenv
from telethon import TelegramClient
from dashboard.state import session_path

load_dotenv()

API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

# One .session SQLite file can't safely be opened by two live TelegramClients at
# once; serialize access per session name so concurrent dashboard requests queue
# instead of hitting "database is locked" or corrupting Telethon's session state.
_session_locks: dict = defaultdict(asyncio.Lock)


def make_client(session_name: str) -> TelegramClient:
    return TelegramClient(session_path(session_name), API_ID, API_HASH)


def session_lock(session_name: str) -> asyncio.Lock:
    return _session_locks[session_name]


if __name__ == "__main__":
    c = make_client("smoke_test_nonexistent")
    assert isinstance(c, TelegramClient)
    print("tg_client.py smoke check OK")
