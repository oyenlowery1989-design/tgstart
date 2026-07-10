#!/usr/bin/env python3
"""
Purge My Messages

A utility to delete your own messages from a specific group or chat.
It scans for groups where you have activity, lets you select one, and then 
deletes all your messages (using the delete_messages API).
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient, types
# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils, tg_utils
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
    ui_utils.print_header("🧹 Self-Destruct Purge")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        ui_utils.print_error("Not authorized. Run login script first.")
        await client.disconnect()
        return

    # 1. Scan for groups with my messages
    ui_utils.print_header("Scanning Your Activity...")
    console.print("[dim]This may take a moment. Finding groups where you have posted...[/dim]")

    me = await client.get_me()
    active_chats = []

    with console.status("[bold yellow]analyzing history...[/bold yellow]") as status:
        async for dialog in client.iter_dialogs(limit=100):
            entity = dialog.entity
            if not isinstance(entity, (types.Channel, types.Chat)):
                continue

            try:
                # Quick check: Do I have at least 1 message here?
                history = await client.get_messages(entity, from_user='me', limit=1)
                if history:
                    # Get exact count
                    total = (await client.get_messages(entity, from_user='me', limit=0)).total
                    active_chats.append({
                        "name": dialog.name,
                        "entity": entity,
                        "count": total,
                        "type": "CHANNEL" if getattr(entity, 'broadcast', False) else "GROUP"
                    })
                    status.update(f"[bold yellow]Found {total} msgs in: {dialog.name}[/bold yellow]")
            except:
                continue

    if not active_chats:
        ui_utils.print_error("No groups found where you have sent messages.")
        await client.disconnect()
        return

    # 2. Display Selection Table
    active_chats.sort(key=lambda x: x['count'], reverse=True)
    table = ui_utils.create_table("Groups/Channels with My Messages", ["#", "Type", "Name", "My Msgs"])
    
    for i, c in enumerate(active_chats, 1):
        table.add_row(str(i), c['type'], c['name'], f"[bold red]{c['count']}[/bold red]")
    
    console.print(table)
    
    choice = console.input(f"\n👉 [bold yellow]Select a group to PURGE (1-{len(active_chats)}) or 'q' to quit: [/bold yellow]").strip().lower()
    
    if choice == 'q':
        await client.disconnect()
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(active_chats)):
        ui_utils.print_error("Invalid selection.")
        await client.disconnect()
        return

    selected = active_chats[int(choice)-1]
    entity = selected['entity']
    total_count = selected['count']

    if total_count == 0:
        ui_utils.print_error("You haven't sent any messages in this group.")
        await client.disconnect()
        return

    # 3. Preview Messages
    ui_utils.print_header(f"Found {total_count} Messages")
    console.print(f"[bold cyan]Reviewing your messages in: {selected['name']}[/bold cyan]")
    
    preview_limit = 10
    console.print(f"\n[bold yellow]--- Last {preview_limit} Messages ---[/bold yellow]")
    
    ids_to_delete = []
    async for msg in client.iter_messages(entity, from_user='me', limit=preview_limit):
        date_str = msg.date.strftime('%Y-%m-%d %H:%M')
        content = (msg.text[:50] + "...") if msg.text else "[Media/Sticker]"
        console.print(f"[dim]{date_str}[/dim] | {content}")
        ids_to_delete.append(msg.id)
    
    if total_count > preview_limit:
        console.print(f"[dim]... and {total_count - preview_limit} older messages.[/dim]")

    console.print("\n[bold red]⚠️  What do you want to do?[/bold red]")
    console.print("1. [red]DELETE ALL[/red] (Permanently remove everything)")
    console.print("2. [green]Cancel[/green] (Keep messages)")
    
    confirm = console.input("\n👉 Choice (1/2): ").strip()
    
    if confirm != "1":
        console.print("[green]Operation cancelled. Your messages are safe.[/green]")
        await client.disconnect()
        return

    # 4. Purge process
    ui_utils.print_header("Purging Messages")
    deleted_count = 0
    # We delete in batches of 100
    try:
        deleted_count = 0 
        while True:
            # Iterate and collect 100 message IDs at a time
            ids_to_delete = []
            async for msg in client.iter_messages(entity, from_user='me', limit=100):
                ids_to_delete.append(msg.id)
            
            if not ids_to_delete:
                break
            
            # Perform the deletion
            # Note: iter_messages finds EVERYTHING (invites, service msgs, etc.)
            # The 'limit=0' count often ignores these service messages.
            await client.delete_messages(entity, ids_to_delete)
            deleted_count += len(ids_to_delete)
            
            # Simple counter update
            console.print(f"[cyan]Deleting... {deleted_count} items removed (this may include hidden service messages)[/cyan]", end="\r")
            
            # Small sleep to be nice to API
            await asyncio.sleep(1)

        console.print("\n")
        ui_utils.print_success(f"Success! Deleted {deleted_count} messages.")
    except Exception as e:
        ui_utils.print_error(f"Purge error: {e}")

    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)
