
"""
FILE: src/utils/tg_utils.py
PURPOSE: Telegram-specific utility functions (group selector, target selector, slugify).
IMPROVEMENTS: Internalized and updated to use relative package imports.
"""
import os
import sys
import re
from . import ui_utils
from .ui_utils import console
from telethon.tl.types import Channel, Chat, User

async def get_entity_info(client, entity_id):
    """
    Resolves an entity and returns its type and participant count.
    Returns: (type_str, member_count)
    """
    try:
        entity = await client.get_entity(entity_id)
        
        # Get member count
        member_count = "?"
        if hasattr(entity, 'participants_count') and entity.participants_count:
            member_count = str(entity.participants_count)
        
        # Determine type
        type_str = "GROUP"
        if isinstance(entity, Channel):
            if getattr(entity, 'broadcast', False):
                type_str = "CHANNEL"
            elif getattr(entity, 'megagroup', False):
                type_str = "SUPERGROUP"
        
        return type_str, member_count
    except:
        return "?", "?"

def slugify(text):
    """
    Makes a string safe for filenames by removing non-alphanumeric chars.
    """
    if not text:
        return "unknown"
    # Keep alphanumeric, spaces, and hyphens, then replace spaces with underscores
    s = re.sub(r'[^\w\s-]', '', text).strip()
    return re.sub(r'[-\s]+', '_', s).lower()

async def pick_group(client):
    """
    Fetches the user's dialogs and allows them to interactively select a group/channel.
    Returns: The selected entity OR None if cancelled.
    """
    ui_utils.print_header("Group Selector")
    
    groups = []
    with console.status("[bold yellow]Fetching your chats...[/bold yellow]"):
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            # Only include Groups and Channels (broadcasts)
            if isinstance(entity, (Channel, Chat)):
                groups.append({
                    "name": dialog.name,
                    "id": entity.id,
                    "entity": entity,
                    "type": "CHANNEL" if getattr(entity, 'broadcast', False) else "GROUP"
                })
            
            # Limit to 100 for performance
            if len(groups) >= 100:
                break

    if not groups:
        ui_utils.print_error("No groups or channels found.")
        return None

    # Sort groups by name
    groups.sort(key=lambda x: x['name'].lower())

    # Create table for selection with additional info
    table = ui_utils.create_table("Recent Groups & Channels", ["#", "Type", "Name", "ID", "Members"])
    table.columns[0].style = "bold magenta"
    table.columns[1].style = "cyan"
    
    for idx, g in enumerate(groups, 1):
        entity = g['entity']
        
        # Get member count if available
        member_count = "?"
        if hasattr(entity, 'participants_count') and entity.participants_count:
            member_count = str(entity.participants_count)
        
        # Check if it's a supergroup (migrated group)
        type_str = g['type']
        if isinstance(entity, Channel) and hasattr(entity, 'megagroup') and entity.megagroup:
            type_str = "SUPERGROUP"
        
        table.add_row(str(idx), type_str, g['name'], str(g['id']), member_count)

    console.print(table)
    
    choice = console.input(f"\n[bold yellow]👉 Select a group (1-{len(groups)}) or 'q' to quit: [/bold yellow]").strip().lower()
    
    if choice == 'q':
        return None
        
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(groups):
            selected = groups[idx]
            ui_utils.print_success(f"Selected: [bold]{selected['name']}[/bold]")
            return selected['entity']
            
    ui_utils.print_error("Invalid selection.")
    return None

async def pick_target(client, default_target):
    """
    Decides the target entity:
    1. Check command line args
    2. If none, ask user to use default or pick from list
    """
    if len(sys.argv) > 1:
        t = sys.argv[1].strip()
        if t.startswith("@"): t = t[1:]
        if re.fullmatch(r"-?\d+", t): return await client.get_entity(int(t))
        return await client.get_entity(t)

    # No arg provided, ask user
    ui_utils.print_header("Target Session")

    # Try to resolve default target name
    default_name = ""
    try:
        # If it's an ID or username, get_entity might work
        entity = await client.get_entity(default_target)
        title = getattr(entity, 'title', getattr(entity, 'first_name', 'Unknown'))
        default_name = f" ({title})"
    except Exception:
        pass  # Ignore errors, just don't show name

    console.print(f"1. Use default ID from script: [bold cyan]{default_target}[/bold cyan]{default_name}")
    console.print("2. [bold green]Pick from my Groups/Channels list[/bold green]")
    
    choice = console.input("\n👉 Choose an option (1 or 2): ").strip()
    
    if choice == "2":
        return await pick_group(client)
    
    # Default to hardcoded default_target
    t = str(default_target).strip()
    if t.startswith("@"): t = t[1:]
    if re.fullmatch(r"-?\d+", t): return await client.get_entity(int(t))
    return await client.get_entity(t)
