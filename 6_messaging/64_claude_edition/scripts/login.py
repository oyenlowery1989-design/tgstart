
import os
import sys
from telethon import TelegramClient
from dotenv import load_dotenv

"""
FILE: login.py
PURPOSE: Simple terminal login script to create .session files.
"""

# Auto-detect project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT_DIR)

load_dotenv()

API_ID = os.getenv("MAIN_API_ID")
API_HASH = os.getenv("MAIN_API_HASH")

if not API_ID or not API_HASH:
    print("❌ Error: MAIN_API_ID or MAIN_API_HASH not found in .env")
    sys.exit(1)

def main():
    session_name = input("Enter a name for this session (e.g. MyBot): ").strip()
    if not session_name:
        print("❌ Session name cannot be empty.")
        return

    # Ensure sessions directory exists
    os.makedirs("sessions", exist_ok=True)
    session_path = os.path.join("sessions", session_name)

    client = TelegramClient(session_path, int(API_ID), API_HASH)

    async def run():
        print(f"\n🚀 Connecting to Telegram for session: {session_name}...")
        await client.start()
        print("\n✅ LOGIN SUCCESSFUL!")
        print(f"File created: sessions/{session_name}.session")
        print("\nNow you can run 'python scripts/get_cloud_string.py' to use this for Render.")

    with client:
        client.loop.run_until_complete(run())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Login cancelled by user.")
        sys.exit(130)
