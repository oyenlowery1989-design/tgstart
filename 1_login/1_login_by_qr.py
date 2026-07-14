import asyncio
"""
QR Code Login Script (Terminal)

This script performs a quick login using a QR code displayed directly in the terminal.
It is a faster alternative to the main login script if you only need QR login.
It requires the 'qrcode-terminal' library.
"""
import os
import time
import sys
from telethon import TelegramClient
import qrcode_terminal

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ui_utils import console, print_header, print_error, print_success

# Load environment variables
load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Use a temporary name so we don't overwrite anything yet
TEMP_SESSION_NAME = os.path.join(ROOT_DIR, "sessions", f"temp_login_{int(time.time())}")
# --------------

async def main():
    print_header("QR Code Login")
    console.print(f"[dim]Starting login process as: {TEMP_SESSION_NAME}...[/dim]")

    if not os.path.exists(os.path.join(ROOT_DIR, "sessions")):
        os.makedirs(os.path.join(ROOT_DIR, "sessions"))

    client = TelegramClient(TEMP_SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    qr = await client.qr_login()
    console.print("\nScan this QR Code with your Telegram App:")
    console.print("Settings → Devices → Link Desktop Device\n")
    qrcode_terminal.draw(qr.url)

    # Wait for scan
    try:
        await qr.wait()
    except Exception as e:
        # Check if it's a 2FA error (SessionPasswordNeededError)
        # Using string check to avoid importing the specific error class if lazy
        if "PasswordNeeded" in str(e) or "password is required" in str(e):
            console.print("\n🔐 Two-Step Verification is enabled.")
            # We need to sign in with the password
            pw = input("Please enter your 2FA password: ").strip()
            await client.sign_in(password=pw)
        else:
            raise e

    # Get user info
    me = await client.get_me()
    username = me.username or f"user_{me.id}"
    print_success(f"Successfully logged in as: @{username} (ID: {me.id})")

    # Important: Disconnect to save the file and release the lock
    await client.disconnect()

    if not os.path.exists(os.path.join(ROOT_DIR, "sessions")):
        os.makedirs(os.path.join(ROOT_DIR, "sessions"))

    # Define target filename inside sessions/ folder
    target_filename = os.path.join(ROOT_DIR, "sessions", f"{username}.session")
    temp_filename = f"{TEMP_SESSION_NAME}.session"  # Now correctly points to sessions/ folder

    # Safety Check: Does the target already exist?
    final_filename = target_filename
    counter = 2
    while os.path.exists(final_filename):
        console.print(f"\n⚠️  '{final_filename}' already exists.")
        final_filename = os.path.join(ROOT_DIR, "sessions", f"{username}({counter}).session")
        counter += 1

    try:
        os.rename(temp_filename, final_filename)
        print_success(f"Session saved as: {final_filename}")
    except Exception as e:
        print_error(f"Error renaming file: {e}")
        console.print(f"ℹ️  Your session is saved as: {temp_filename}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print_error("Process cancelled by user. Exiting safely...")
        # Cleanup temp session file if it exists
        temp_file = f"{TEMP_SESSION_NAME}.session"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        sys.exit(0)
