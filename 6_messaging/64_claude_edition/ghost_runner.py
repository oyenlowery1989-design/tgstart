#!/usr/bin/env python3
"""
64_ghost_mirror_multiple_claude.py (Refactored)

Enhanced Ghost Mirror with Modular Architecture
"""

import asyncio
import os
import sys
import traceback
import subprocess
from dotenv import load_dotenv
from telethon import TelegramClient

# Internal Utils
from src.utils import ui_utils, tg_utils

# Import Modular Components
from src.config.settings import TIMEZONE_STR
from src.core.logger import log_error, rotate_old_logs, console, ensure_log_dirs
from src.core.user_intelligence import load_users_index, bio_worker
from src.config.loader import load_config, save_config, CONFIG_FILE
from src.core.state import StateManager

# Import Handlers (Renamed for friendliness)
from src.handlers.handle_messages import MessageHandler
from src.handlers.handle_reactions import ReactionHandler
from src.handlers.handle_admin_actions import AdminActionHandler
from src.handlers.handle_members import MemberHandler
from src.handlers.handle_deletions import DeletionHandler
from src.core.prefetcher import start_prefetch_task

load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

if not API_ID or not API_HASH:
    console.print("[bold red]❌ ERROR: API_ID or API_HASH missing in .env file![/bold red]")
    console.print("[yellow]Please ensure your .env file exists and contains these variables.[/yellow]")
    sys.exit(1)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Session selection
default_session = os.getenv("DEFAULT_SESSION", None)
if default_session:
    SESSION_NAME = default_session if os.path.isabs(default_session) else os.path.join(ROOT_DIR, default_session)
else:
    SESSION_NAME = None 

LAST_SESSION_FILE = os.path.join(os.path.dirname(CONFIG_FILE), "last_session.txt")

def select_session_interactively():
    """
    Scans for .session files and lets user choose one. Returns full path without extension.
    """
    sessions_dir = os.path.join(ROOT_DIR, "sessions")
    
    if not os.path.exists(sessions_dir):
        console.print(f"[red]Sessions directory not found: {sessions_dir}[/red]")
        return None
    
    # Find all .session files
    session_files = []
    for file in os.listdir(sessions_dir):
        if file.endswith(".session"):
            session_name = file[:-8]  # Remove .session extension
            session_files.append(session_name)
    
    if not session_files:
        console.print(f"[yellow]No session files found in {sessions_dir}[/yellow]")
        choice = console.input("Would you like to login to a new session? [Y/n]: ").strip().lower()
        if choice in ('', 'y', 'yes'):
            login_script = os.path.join(ROOT_DIR, "scripts", "login.py")
            console.print(f"\n[bold cyan]Starting login process...[/bold cyan]")
            try:
                subprocess.check_call([sys.executable, login_script])
                return select_session_interactively()
            except subprocess.CalledProcessError:
                console.print(f"\n[yellow]↩ Returned to prompt.[/yellow]")
                return select_session_interactively()
            except Exception as e:
                console.print(f"[red]Error during login: {e}[/red]")
                return None
        return None
    
    # Load last used session
    last_session = None
    if os.path.exists(LAST_SESSION_FILE):
        try:
            with open(LAST_SESSION_FILE, 'r', encoding='utf-8') as f:
                last_session = f.read().strip()
        except:
            pass
    
    # If we have a last session, ask if user wants to use it
    if last_session and last_session in session_files:
        ui_utils.print_header("📱 Select Telegram Session")
        console.print(f"[cyan]Last used session:[/cyan] [bold white]{last_session}[/bold white]\n")
        choice = console.input("Use this session? [Y/n]: ").strip().lower()
        
        if choice in ('', 'y', 'yes'):
            session_path = os.path.join(sessions_dir, last_session)
            console.print(f"[green]✓ Using: {last_session}[/green]\n")
            return session_path
    
    # Display menu
    ui_utils.print_header("📱 Select Telegram Session")
    console.print("[cyan]Available sessions:[/cyan]\n")
    
    for i, session_name in enumerate(session_files, 1):
        # Highlight the last used session
        if session_name == last_session:
            console.print(f"[bold white]{i}.[/bold white] {session_name} [dim](last used)[/dim]")
        else:
            console.print(f"[bold white]{i}.[/bold white] {session_name}")
    
    console.print(f"\n[bold white]L.[/bold white] Login to New Session")
    console.print(f"[bold white]Q.[/bold white] Quit")
    
    # Get user selection
    while True:
        choice = console.input("\n👉 [bold yellow]Select session number (or L/Q): [/bold yellow]").strip().lower()
        
        if choice == 'q':
            return None
        
        if choice == 'l':
            # Run login script
            login_script = os.path.join(ROOT_DIR, "scripts", "login.py")
            console.print(f"\n[bold cyan]Starting login process...[/bold cyan]")
            try:
                # We use check_call to block until finished
                subprocess.check_call([sys.executable, login_script])
                # After return, re-run session selection to see the new file
                return select_session_interactively()
            except subprocess.CalledProcessError:
                # User likely cancelled (Ctrl+C in login.py)
                console.print(f"\n[yellow]↩ Returned to session selection.[/yellow]")
                return select_session_interactively()
            except Exception as e:
                console.print(f"[red]Error during login: {e}[/red]")
                continue

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(session_files):
                selected = session_files[idx]
                session_path = os.path.join(sessions_dir, selected)
                
                # Save this as the last used session
                try:
                    with open(LAST_SESSION_FILE, 'w', encoding='utf-8') as f:
                        f.write(selected)
                except:
                    pass
                
                console.print(f"[green]✓ Selected: {selected}[/green]\n")
                return session_path
        
        console.print("[red]Invalid selection. Try again.[/red]")

async def main():
    global SESSION_NAME
    
    ensure_log_dirs()
    load_users_index()
    rotate_old_logs()
    
    ui_utils.print_header("👻 Ultimate Ghost Mirror (Modular v5)")
    console.print(f"[dim]Refactored Architecture with Isolated Handlers[/dim]")
    console.print(f"[dim]Timezone: {TIMEZONE_STR}[/dim]\n")
    
    # Select session if not set via env
    if SESSION_NAME is None:
        SESSION_NAME = select_session_interactively()
        if not SESSION_NAME:
            console.print("[red]No session selected. Exiting.[/red]")
            return
    
    # Session path logic
    if os.path.isabs(SESSION_NAME):
        sess_path = SESSION_NAME
    else:
        # If it's just a name, assume it's in sessions dir
        if not SESSION_NAME.startswith("sessions") and not os.sep in SESSION_NAME:
             sess_path = os.path.join(ROOT_DIR, "sessions", SESSION_NAME)
        else:
             sess_path = os.path.join(ROOT_DIR, SESSION_NAME)

    client = TelegramClient(sess_path, API_ID, API_HASH)
    
    try:
        await client.connect()
    except Exception as e:
        if "database is locked" in str(e).lower():
            ui_utils.print_error("ERROR: Session database is locked! Close other scripts.")
            return
        else:
            ui_utils.print_error(f"Connect failed: {e}")
            log_error("startup", f"Connection failed: {e}", traceback.format_exc())
            return
    
    if not await client.is_user_authorized():
        ui_utils.print_error("Not authorized. Run login script first.")
        await client.disconnect()
        return
    
    # Start Bio Worker
    asyncio.create_task(bio_worker(client))

    # Management Menu
    while True:
        pairs_data = load_config()
        
        # If we have a default session and existing pairs, start automatically (Non-interactive mode)
        if default_session and pairs_data:
            ui_utils.print_header(f"Ghost Mirror Auto-Start ({default_session})")
            console.print("[green]Starting monitoring automatically...[/green]")
            break

        ui_utils.print_header("👻 Ghost Config")
        
        if not pairs_data:
            console.print("[yellow]No ghost mirrors configured.[/yellow]")
        else:
            table = ui_utils.create_table("Active Mirrors", ["#", "Source", "Type", "ID", "👥", "➔", "Backup", "Type", "ID", "👥"])
            
            # Fetch member counts and types for each group
            for i, p in enumerate(pairs_data, 1):
                src_type, src_members = await tg_utils.get_entity_info(client, p['source_id'])
                dst_type, dst_members = await tg_utils.get_entity_info(client, p['dest_id'])

                table.add_row(
                    str(i), 
                    p['source_title'], 
                    src_type, 
                    str(p['source_id']), 
                    src_members,
                    "➔", 
                    p['dest_title'],
                    dst_type,
                    str(p['dest_id']),
                    dst_members
                )
            console.print(table)
            console.print("\n[dim]Note: Active User/Member counts are fetched live from Telegram.[/dim]")

        console.print("\n[bold cyan][S][/bold cyan] Start Monitoring")
        console.print("[bold green][A][/bold green] Add Pair")
        if pairs_data:
            console.print("[bold red][D][/bold red] Delete Pair")
        console.print("[bold white][Q][/bold white] Quit")
        
        action = console.input("\n👉 [bold yellow]Select: [/bold yellow]").strip().lower()
        
        if action == 's':
            if not pairs_data: continue
            break
        elif action == 'a':
            console.print("\n[cyan]Select Source:[/cyan]")
            src = await tg_utils.pick_group(client)
            if not src: continue
            console.print("[cyan]Select Destination:[/cyan]")
            dst = await tg_utils.pick_group(client)
            if not dst: continue
            pairs_data.append({
                "source_id": src.id, "dest_id": dst.id,
                "source_title": getattr(src, 'title', str(src.id)),
                "dest_title": getattr(dst, 'title', str(dst.id))
            })
            save_config(pairs_data)
        elif action == 'd' and pairs_data:
            idx = console.input(f"\nEnter # (1-{len(pairs_data)}): ")
            if idx.isdigit() and 1 <= int(idx) <= len(pairs_data):
                pairs_data.pop(int(idx)-1)
                save_config(pairs_data)
        elif action == 'q':
            await client.disconnect()
            return

    # --- Initialize State & Handlers ---
    state_manager = StateManager()
    await asyncio.gather(*state_manager.load_pairs(client, pairs_data, console))
    
    if not state_manager.mirror_map:
        console.print("[bold red]❌ ERROR: No active pairs could be loaded. Check IDs and bot permissions.[/bold red]")
        await client.disconnect()
        return

    # Register Handlers
    handlers = [
        MessageHandler(client, state_manager),
        ReactionHandler(client, state_manager),
        AdminActionHandler(client, state_manager),
        MemberHandler(client, state_manager),
        DeletionHandler(client, state_manager)
    ]
    
    for h in handlers:
        await h.register()

    # --- Start Modular Background Passive Tasks ---
    await start_prefetch_task(client, state_manager)

    console.print("\n[dim]Ghost Mirror Active. Modular architecture loaded.[/dim]\n")
    try:
        await client.run_until_disconnected()
    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as e:
        log_error("main_loop", str(e), traceback.format_exc())
    finally:
        console.print("\n[bold yellow]🛑 Received shutdown signal. Disconnecting...[/bold yellow]")
        await client.disconnect()
        ui_utils.print_success("Shutdown complete.")

if __name__ == "__main__":
    try: 
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError): 
        sys.exit(0)
    except Exception as e:
        log_error("startup_fatal", str(e), traceback.format_exc())
        sys.exit(1)
