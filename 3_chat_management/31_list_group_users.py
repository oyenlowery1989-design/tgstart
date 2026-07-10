#!/usr/bin/env python3
"""
List Group Members

This script fetches all members (participants) from a specific target group.
It saves the user details (ID, Username, Name, Phone) to a CSV file.
"""
import asyncio
import csv
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import User
# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils, tg_utils
from utils.ui_utils import console

load_dotenv()

# =========================
# Configuration
# =========================

API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_NAME = os.getenv("DEFAULT_SESSION", os.path.join(ROOT_DIR, "sessions", "TonkinStuart"))

# If it's a relative path, make it absolute relative to ROOT_DIR
if not os.path.isabs(SESSION_NAME):
    SESSION_NAME = os.path.join(ROOT_DIR, SESSION_NAME)

# Replace with target group ID
TARGET_GROUP = 1623947149

# Off by default: phone numbers are PII and this scrapes the whole group roster.
# Set EXPORT_PHONE_NUMBERS=true in .env to include them in the CSV.
EXPORT_PHONE_NUMBERS = os.getenv("EXPORT_PHONE_NUMBERS", "false").strip().lower() == "true"

# Off by default: aggressive mode hammers Telegram's API harder to pull more of the
# roster (risks FloodWait/ToS friction). Set AGGRESSIVE_SCRAPE=true in .env to enable.
AGGRESSIVE_SCRAPE = os.getenv("AGGRESSIVE_SCRAPE", "false").strip().lower() == "true"

# =========================
# Main logic
# =========================

async def main():
    ui_utils.print_header("Listing Group Users")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    with console.status("[bold yellow]Connecting to Telegram...[/bold yellow]"):
        await client.start()

    try:
        # Resolve the entity using the interactive picker
        entity = await tg_utils.pick_target(client, TARGET_GROUP)
        if not entity:
            ui_utils.print_error("No group selected. Exiting.")
            return

        ui_utils.print_header(f"Group: {entity.title} ({entity.id})")
        
        users = []
        with ui_utils.get_progress() as progress:
            task = progress.add_task("Fetching members...", total=None) # indeterminate
            async for user in client.iter_participants(entity, aggressive=AGGRESSIVE_SCRAPE):
                if not isinstance(user, User):
                    continue
                    
                users.append({
                    "id": user.id,
                    "username": user.username or "",
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "phone": user.phone or "",
                    "bot": user.bot
                })
                progress.update(task, description=f"Found [bold cyan]{len(users)}[/bold cyan] users...")

        if not os.path.exists("31_data"):
            os.makedirs("31_data")

        # Generate filenames
        safe_id = str(entity.id).replace("-", "n")
        safe_name = tg_utils.slugify(getattr(entity, 'title', ''))
        count_str = str(len(users))
        out_csv = os.path.join("31_data", f"31_users_{safe_name}_{safe_id}_{count_str}.csv")

        # -------- Save CSV --------
        header = ["group_name", "group_id", "id", "username", "first_name", "last_name"]
        if EXPORT_PHONE_NUMBERS:
            header.append("phone")
        header.append("is_bot")

        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for u in users:
                row = [entity.title, entity.id, u["id"], u["username"], u["first_name"], u["last_name"]]
                if EXPORT_PHONE_NUMBERS:
                    row.append(u["phone"])
                row.append(u["bot"])
                writer.writerow(row)

        ui_utils.print_success(f"Fetched {len(users)} users.")
        console.print(f"- [dim]{out_csv}[/dim]")
        if not EXPORT_PHONE_NUMBERS:
            console.print("[dim]Phone numbers omitted (set EXPORT_PHONE_NUMBERS=true in .env to include).[/dim]")

    except Exception as e:
        ui_utils.print_error(str(e))
        console.print("[yellow]Tip: Ensure you are a member of the group. Cannot fetch members from channels unless you are admin.[/yellow]")

    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]⛔ Process cancelled by user. Exiting safely...[/bold red]")
        sys.exit(0)
