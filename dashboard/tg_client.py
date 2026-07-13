"""Builds TelegramClient instances using the suite's MAIN_API_ID/API_ID fallback convention."""
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from dashboard.state import session_path

load_dotenv()

API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))


def make_client(session_name: str) -> TelegramClient:
    return TelegramClient(session_path(session_name), API_ID, API_HASH)


if __name__ == "__main__":
    c = make_client("smoke_test_nonexistent")
    assert isinstance(c, TelegramClient)
    print("tg_client.py smoke check OK")
