#!/usr/bin/env python3
"""
Group Analytics & Statistics

This script analyzes a target group's message history to generate statistics.
It identifies top influencers (most active users) and peak activity hours.
Results are displayed in the terminal and saved to a CSV file.
"""
import asyncio
import csv
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from telethon import TelegramClient
from telethon.tl.types import Message
# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils, tg_utils
from utils.ui_utils import console
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_NAME = os.getenv("DEFAULT_SESSION", os.path.join(ROOT_DIR, "sessions", "TonkinStuart"))

# If it's a relative path, make it absolute relative to ROOT_DIR
if not os.path.isabs(SESSION_NAME):
    SESSION_NAME = os.path.join(ROOT_DIR, SESSION_NAME)

# Default target if not picking
DEFAULT_TARGET = 1623947149
SCAN_LIMIT = 2000 # Default limit for stats

OUT_DIR = "50_data"

async def main():
    ui_utils.print_header("Group Analytics & Influencers")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        ui_utils.print_error("Not authorized. Run login script first.")
        await client.disconnect()
        return

    entity = await tg_utils.pick_target(client, DEFAULT_TARGET)
    if not entity:
        await client.disconnect()
        return

    ui_utils.print_header(f"Analyzing: {getattr(entity, 'title', 'Group')}")
    
    limit_input = console.input(f"\n[cyan]How many messages to analyze? (default {SCAN_LIMIT}): [/cyan]").strip()
    limit = int(limit_input) if limit_input.isdigit() else SCAN_LIMIT

    user_msgs = Counter()
    user_names = {}
    hours = Counter()
    total_scanned = 0
    
    with ui_utils.get_progress() as progress:
        task = progress.add_task("Gathering stats...", total=limit)
        
        async for msg in client.iter_messages(entity, limit=limit):
            if not isinstance(msg, Message): continue
            
            total_scanned += 1
            
            # User stats
            if msg.sender_id:
                user_msgs[msg.sender_id] += 1
                if msg.sender_id not in user_names:
                    sender = getattr(msg, 'sender', None)
                    if sender:
                        name = f"@{sender.username}" if getattr(sender, 'username', None) else f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip()
                        user_names[msg.sender_id] = name or f"ID:{msg.sender_id}"

            # Time stats
            if msg.date:
                hours[msg.date.hour] += 1
                
            progress.advance(task)

    ui_utils.print_success(f"Analysis complete! Scanned {total_scanned} messages.")

    # Prepare Tables
    # 1. Top Influencers
    top_users = user_msgs.most_common(10)
    user_table = ui_utils.create_table("Top 10 Influencers (Most Active)", ["Rank", "User", "Messages", "%"])
    for i, (uid, count) in enumerate(top_users, 1):
        perc = (count / total_scanned) * 100
        user_table.add_row(str(i), user_names.get(uid, str(uid)), str(count), f"{perc:.1f}%")

    # 2. Peak Activity
    peak_hours = hours.most_common(5)
    time_table = ui_utils.create_table("Peak Activity Hours (UTC)", ["Hour", "Messages"])
    for hr, count in sorted(peak_hours):
        time_table.add_row(f"{hr:02}:00", str(count))

    console.print(user_table)
    console.print(time_table)

    # Save to CSV
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)
    
    safe_name = tg_utils.slugify(getattr(entity, 'title', ''))
    safe_id = str(entity.id).replace("-", "n")
    filename = os.path.join(OUT_DIR, f"stats_{safe_name}_{safe_id}.csv")
    
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value", "Count/Details"])
        writer.writerow(["GROUP_TITLE", getattr(entity, 'title', 'N/A'), str(entity.id)])
        writer.writerow(["SCAN_TOTAL", str(total_scanned), ""])
        writer.writerow([])
        writer.writerow(["TOP_USERS"])
        for uid, count in user_msgs.most_common(50):
            writer.writerow(["User", user_names.get(uid, str(uid)), str(count)])
        writer.writerow([])
        writer.writerow(["HOURLY_ACTIVITY"])
        for hr in range(24):
            writer.writerow(["Hour", f"{hr:02}:00", str(hours[hr])])

    ui_utils.print_success(f"Full stats saved to: [bold]{filename}[/bold]")
    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]⛔ Cancelled. Exiting...[/bold red]")
        sys.exit(0)
