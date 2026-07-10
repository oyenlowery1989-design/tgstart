import asyncio
"""
Advanced Session Verifier

This script scans the 'sessions/' directory for all .session files and verifies their status.
It provides a menu to check individual sessions or mass-verify all of them, reporting
status (Active/Invalid) and user details.
"""
import os
import glob
import sys
from dotenv import load_dotenv
from telethon import TelegramClient
# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils
from utils.ui_utils import console

load_dotenv()

# =========================
# Configuration
# =========================

API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSIONS_DIR = os.path.join(ROOT_DIR, "sessions")

# =========================
# Main Logic
# =========================

def list_sessions():
    """Finds all .session files in the sessions/ folder."""
    if not os.path.exists(SESSIONS_DIR):
        ui_utils.print_error(f"'{SESSIONS_DIR}' directory not found.")
        return []
    
    files = glob.glob(os.path.join(SESSIONS_DIR, "*.session"))
    sessions = []
    
    for f in files:
        filename = os.path.basename(f)
        name = os.path.splitext(filename)[0]
        # Ignore temp sessions if any are left
        if not name.startswith("temp_login_"):
            sessions.append(name)
        
    return sorted(sessions)

async def check_session(session_name, results_table=None):
    """Attempts to connect using the given session name."""
    session_path = os.path.join(SESSIONS_DIR, session_name)
    
    client = TelegramClient(session_path, API_ID, API_HASH)
    status = "Unknown"
    details = ""
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            status = "[bold red]INVALID[/bold red]"
            details = "Revoked or expired"
        else:
            me = await client.get_me()
            status = "[bold green]ACTIVE[/bold green]"
            user_display = f"@{me.username}" if me.username else f"{me.first_name} {me.last_name or ''}"
            details = f"{user_display} (ID: {me.id})"
            
    except Exception as e:
        status = "[bold red]ERROR[/bold red]"
        details = str(e)
    finally:
        await client.disconnect()
        if results_table:
            results_table.add_row(session_name, status, details)

async def main():
    ui_utils.print_header("TELEGRAM SESSION VERIFIER")
    
    sessions = list_sessions()
    
    if not sessions:
        ui_utils.print_error("No sessions found in 'sessions/' folder.")
        console.print("   Please run '1_login.py' to add an account first.")
        return

    console.print("\n[bold]Found the following sessions:[/bold]")
    for idx, name in enumerate(sessions, 1):
        console.print(f" {idx}. [yellow]{name}[/yellow]")
    console.print(f" {len(sessions) + 1}. [bold green][Check ALL][/bold green]")

    choice = console.input(f"\n[bold yellow]👉 Select a session to verify (1-{len(sessions) + 1}): [/bold yellow]").strip()
    
    table = ui_utils.create_table("Session Verification Results", ["Session Name", "Status", "Details"])
    table.columns[0].style = "cyan"
    table.columns[1].justify = "center"
    table.columns[2].style = "dim"

    if choice == str(len(sessions) + 1):
        with ui_utils.get_progress() as progress:
            task = progress.add_task("Verifying all sessions...", total=len(sessions))
            for name in sessions:
                progress.update(task, description=f"Checking [yellow]{name}[/yellow]...")
                await check_session(name, table)
                progress.advance(task)
        console.print(table)
    
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            target = sessions[idx]
            with console.status(f"[bold yellow]Checking {target}...[/bold yellow]"):
                await check_session(target, table)
            console.print(table)
        else:
            ui_utils.print_error("Invalid selection.")
    else:
        ui_utils.print_error("Invalid input.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]⛔ Process cancelled by user. Exiting safely...[/bold red]")
        sys.exit(0)
