import asyncio
"""
Basic Session Verification

A simple script to check if a specific Telegram session is valid and active.
It attempts to connect and print the current user's details.
"""
from telethon import TelegramClient

import os
import sys
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
api_hash = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
session_name = os.getenv("DEFAULT_SESSION", os.path.join(ROOT_DIR, "sessions", "TonkinStuart"))

# If it's a relative path, make it absolute relative to ROOT_DIR
if not os.path.isabs(session_name):
    session_name = os.path.join(ROOT_DIR, session_name)

client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start()  # should not ask phone
    me = await client.get_me()
    print("✅ Logged in as:", me.id, me.username or me.first_name)
    await client.send_message("me", "✅ Session reuse works")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\n\n⛔ Process cancelled by user. Exiting safely...")
        sys.exit(0)
