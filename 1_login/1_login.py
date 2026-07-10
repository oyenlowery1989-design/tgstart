import asyncio
"""
Interactive Login Script (Phone & QR)

This script provides an interactive menu to log in to Telegram using either
a phone number (with code verification) or a QR code (using an image file).
It handles 2FA (Two-Step Verification) if enabled and saves the session securely.
"""
import os
import subprocess
import time
import sys
from telethon import TelegramClient, errors
import qrcode

from dotenv import load_dotenv
# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils
from utils.ui_utils import console

# Load environment variables
load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Use a temporary name so we don't overwrite anything yet
TEMP_SESSION_NAME = os.path.join(ROOT_DIR, "sessions", f"temp_login_{int(time.time())}")
# --------------

async def login_qr(client):
    """
    Handles QR Code Login Flow with Image File
    """
    try:
        qr_obj = await client.qr_login()
        
        # Create QR Image
        img = qrcode.make(qr_obj.url)
        img_filename = "login_qr.png"
        img.save(img_filename)

        ui_utils.print_header("Generate QR Code")
        console.print(f"👉 [bold green]OPEN THIS FILE:[/bold green] [underline]{os.path.abspath(img_filename)}[/underline]")
        console.print("    Scan it with your Telegram App: [cyan]Settings → Devices → Link Desktop Device[/cyan]\n")
        
        # Try to open automatically
        if sys.platform == 'win32':
            os.startfile(img_filename)
        elif sys.platform == 'darwin':
            subprocess.run(["open", img_filename])
        else:
            subprocess.run(["xdg-open", img_filename])

        with console.status("[bold yellow]Waiting for scan...[/bold yellow]"):
            await qr_obj.wait()
        
        # Cleanup image
        try:
            os.remove(img_filename)
        except:
            pass
            
        return True
    except errors.SessionPasswordNeededError:
        # Prompt for 2FA inside the flow
        return await handle_2fa(client)
    except Exception as e:
        # If QR login fails for some reason (e.g. 2FA triggered late)
        if "PasswordNeeded" in str(e) or "password is required" in str(e):
             return await handle_2fa(client)
        ui_utils.print_error(f"QR Login Error: {e}")
        return False
    finally:
         # Cleanup image in all cases
        try:
            if os.path.exists("login_qr.png"):
                os.remove("login_qr.png")
        except:
            pass

async def login_phone(client):
    """
    Handles Phone Number Login Flow
    """
    phone = console.input("\n[cyan]📱 Enter your phone number (e.g., +1234567890): [/cyan]").strip()
    
    try:
        await client.send_code_request(phone)
    except errors.FloodWaitError as e:
        ui_utils.print_error(f"Too many attempts. Please wait {e.seconds} seconds.")
        return False
    except Exception as e:
        ui_utils.print_error(f"Error sending code: {e}")
        return False

    code = console.input("[cyan]📩 Enter the code you received: [/cyan]").strip()
    
    try:
        await client.sign_in(phone, code)
        return True
    except errors.SessionPasswordNeededError:
        return await handle_2fa(client)
    except errors.PhoneCodeInvalidError:
        print("\n❌ Invalid code.")
        return False
    except Exception as e:
         if "PasswordNeeded" in str(e) or "password is required" in str(e):
             return await handle_2fa(client)
         ui_utils.print_error(f"Error signing in: {e}")
         return False

async def handle_2fa(client):
    """
    Handles 2FA Password Input
    """
    console.print("\n[bold yellow]🔐 Two-Step Verification is enabled.[/bold yellow]")
    pw = console.input("[cyan]🔑 Please enter your 2FA password: [/cyan]").strip()
    try:
        await client.sign_in(password=pw)
        return True
    except Exception as e:
        ui_utils.print_error(f"Login Failed: {e}")
        return False

async def main():
    ui_utils.print_header("Telegram Login Manager")
    console.print("1. [cyan]Login via QR Code[/cyan] (Best experience)")
    console.print("2. [cyan]Login via Phone Number[/cyan] (Classic)")
    
    choice = console.input("\n[bold yellow]👉 Choose an option (1 or 2): [/bold yellow]").strip()

    if not os.path.exists(os.path.join(ROOT_DIR, "sessions")):
        os.makedirs(os.path.join(ROOT_DIR, "sessions"))

    console.print(f"\n🔄 Starting session: [yellow]{TEMP_SESSION_NAME}[/yellow]...")
    client = TelegramClient(TEMP_SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    success = False
    if choice == "1":
        success = await login_qr(client)
    elif choice == "2":
        success = await login_phone(client)
    else:
        print("\n❌ Invalid choice. Exiting.")
        await client.disconnect()
        return

    if success:
        # Get user info
        me = await client.get_me()
        username = me.username or f"user_{me.id}"
        ui_utils.print_success(f"Successfully logged in as: [bold cyan]@{username}[/bold cyan] (ID: {me.id})")

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
            console.print(f"\n[red]⚠️  '{final_filename}' already exists.[/red]")
            final_filename = os.path.join("sessions", f"{username}({counter}).session")
            counter += 1
        
        try:
            os.rename(temp_filename, final_filename)
            ui_utils.print_success(f"Session saved as: [bold]{final_filename}[/bold]")
        except Exception as e:
            ui_utils.print_error(f"Error renaming file: {e}")
            console.print(f"ℹ️  Your session is saved as: [dim]{temp_filename}[/dim]")
    else:
        ui_utils.print_error("Login failed or cancelled.")
        await client.disconnect()
        # Clean up temp file
        if os.path.exists(f"{TEMP_SESSION_NAME}.session"):
            os.remove(f"{TEMP_SESSION_NAME}.session")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]⛔ Process cancelled by user. Exiting safely...[/bold red]")
        sys.exit(0)
