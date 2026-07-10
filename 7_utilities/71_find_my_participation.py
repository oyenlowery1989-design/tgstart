#!/usr/bin/env python3
"""
Find My Participation

Scans all your dialogs to find chats where you have sent at least one message.
Useful for auditing your account activity and finding old groups you participated in.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient, types, utils
# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils
from utils.ui_utils import console

load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_NAME = os.getenv("DEFAULT_SESSION", os.path.join(ROOT_DIR, "sessions", "TonkinStuart"))

# If it's a relative path, make it absolute relative to ROOT_DIR
if not os.path.isabs(SESSION_NAME):
    SESSION_NAME = os.path.join(ROOT_DIR, SESSION_NAME)

async def main():
    ui_utils.print_header("🔍 Participation Searcher (Where have I posted?)")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        ui_utils.print_error("Not authorized. Run login script first.")
        await client.disconnect()
        return

    me = await client.get_me()
    ui_utils.print_success(f"Searching chats for messages from: [bold cyan]@{me.username or me.first_name}[/bold cyan]")
    
    participated_chats = []
    
    table = ui_utils.create_table("My Active Participation", ["Type", "Chat Name", "ID", "Message Count"])
    
    with console.status("[bold yellow]Scanning your dialogs...[/bold yellow]") as status:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if not isinstance(entity, (types.Channel, types.Chat)):
                continue
                
            status.update(f"[bold yellow]Checking: {dialog.name}[/bold yellow]")
            
            try:
                # Search for any message sent by 'me' in this chat
                # We limit to 1 just to see if we have ANY activity
                history = await client.get_messages(entity, from_user='me', limit=1)
                
                if history:
                    # If we found at least one, count how many (up to 100 for speed)
                    # Note: Full count can be slow on large groups
                    total_from_me = await client.get_messages(entity, from_user='me', limit=0)
                    count = total_from_me.total
                    
                    chat_type = "CHANNEL" if getattr(entity, 'broadcast', False) else "GROUP"
                    participated_chats.append((chat_type, dialog.name, entity.id, count))
                    table.add_row(chat_type, dialog.name, str(entity.id), f"[bold green]{count}[/bold green]")
            except Exception:
                # Some chats might have restricted history search
                continue

    if not participated_chats:
        ui_utils.print_error("No chats found where you have sent messages.")
    else:
        console.print("\n")
        console.print(table)
        ui_utils.print_success(f"Scan complete. Found {len(participated_chats)} chats with your messages.")

    input("\n[dim][Press Enter to exit][/dim]")
    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)
