#!/usr/bin/env python3
"""
List All Dialogs (Chats/Groups/Channels)

This script fetches all open dialogs (conversations) for the logged-in account.
It categorizes them (User, Group, Channel) and saves the list to a CSV file.
Useful for finding group IDs.
"""
import asyncio
import csv
import os
import sys
from dotenv import load_dotenv
# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils
from utils.ui_utils import console
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

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

OUT_DIR = "30_data"
OUT_CSV = os.path.join(OUT_DIR, "30_dialogs.csv")

# =========================
# Main logic
# =========================

async def main():
    ui_utils.print_header("Listing Telegram Dialogs")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    with console.status("[bold yellow]Connecting and fetching dialogs...[/bold yellow]"):
        await client.start()

        if not os.path.exists(OUT_DIR):
            os.makedirs(OUT_DIR)

        rows = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            dialog_type = "UNKNOWN"
            if isinstance(entity, Channel):
                dialog_type = "CHANNEL" if entity.broadcast else "GROUP"
            elif isinstance(entity, Chat):
                dialog_type = "GROUP"
            elif isinstance(entity, User):
                dialog_type = "USER"

            rows.append({
                "name": dialog.name,
                "id": entity.id,
                "type": dialog_type,
                "username": getattr(entity, "username", None),
            })

    # -------- Display Table --------
    table = ui_utils.create_table("Found Dialogs", ["Type", "Name", "ID", "Username"])
    table.columns[0].style = "cyan"
    table.columns[1].style = "bold white"
    table.columns[2].style = "dim"
    
    for r in rows[:20]: # Show first 20 for preview
        table.add_row(r["type"], r["name"], str(r["id"]), f"@{r['username']}" if r['username'] else "")
    
    console.print(table)
    if len(rows) > 20:
        console.print(f" (Plus {len(rows)-20} more dialogs saved to files...)\n")

    # -------- Save CSV --------
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "name", "id", "username"])
        for r in rows:
            writer.writerow([r["type"], r["name"], r["id"], r["username"]])

    ui_utils.print_success(f"Saved {len(rows)} dialogs:")
    console.print(f"- [dim]{OUT_CSV}[/dim]")

    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]⛔ Process cancelled by user. Exiting safely...[/bold red]")
        sys.exit(0)
