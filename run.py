import os
"""
Main Menu Launcher

The central entry point for the Telegram Automation Suite.
Provides an interactive terminal menu to easy launch any of the other scripts
(Login, Verify, Chats, Scraping, Monitoring, Messaging, Utils).
"""
import sys
import subprocess
import time
from utils import ui_utils
from utils.ui_utils import console, box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_script(script_path, args=None, cwd=None):
    """Runs a python script as a separate process."""
    cmd = [sys.executable, os.path.basename(script_path) if cwd else script_path]
    if args:
        cmd.extend(args)

    try:
        subprocess.run(cmd, cwd=cwd)
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed to run {script_path}: {e}[/bold red]")

    console.print("\n[dim][Press Enter to return to menu][/dim]")
    input()

def run_dashboard_pair(cwd):
    """Starts the mirror bot (run.py watchdog) in the background, then the dashboard UI in the foreground.

    GhostMirror v4.0 (65/) needs both processes per its own README: the bot connects
    to Telegram and mirrors messages, the dashboard is just the config/monitoring UI.
    """
    bot_proc = subprocess.Popen([sys.executable, "run.py"], cwd=cwd)
    try:
        console.print("[dim]Mirror bot started in background. Launching dashboard...[/dim]")
        subprocess.run([sys.executable, "dashboard.py"], cwd=cwd)
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed to run dashboard: {e}[/bold red]")
    finally:
        bot_proc.terminate()
        bot_proc.wait()

    console.print("\n[dim][Press Enter to return to menu][/dim]")
    input()

def main():
    while True:
        clear_screen()
        
        # Header Panel
        console.print(Panel(
            Text("TELEGRAM SCRAPER MANAGER", justify="center", style="bold cyan"),
            box=box.DOUBLE,
            border_style="bright_blue"
        ))

        # Menu Table
        table = Table(show_header=False, box=box.ROUNDED, expand=True, border_style="bright_black")
        table.add_column("Choice", style="bold magenta", width=5)
        table.add_column("Icon", width=3)
        table.add_column("Description", style="white")

        table.add_row("1", "🔑", "Login / Add New Account")
        table.add_row("2", "🔍", "Verify & List Sessions")
        table.add_row("3", "💬", "List My Chats/Groups")
        table.add_row("4", "👥", "List Users in a Group")
        table.add_row("5", "🔗", "Extract Links from Group")
        table.add_row("6", "📊", "Group Analytics & Stats")
        table.add_row("7", "🛡️", "Ghost Mirror - Claude Edition (Forensics)")
        table.add_row("8", "🛰️", "Ghost Mirror - Dashboard (v4.0)")
        table.add_row("11", "🔍", "Find Chats with My Messages")
        table.add_row("12", "🧹", "Self-Destruct (Purge My Messages)")
        table.add_row("", "", "")
        table.add_row("0", "🚪", "Exit")

        console.print(table)
        
        choice = console.input("[bold yellow]👉 Choose an option: [/bold yellow]").strip()
        
        if choice == "1":
            run_script("1_login/1_login.py")
        elif choice == "2":
            run_script("2_verify/2_verify_login_advanced.py")
        elif choice == "3":
            run_script("3_chat_management/30_list_chats.py")
        elif choice == "4":
            run_script("3_chat_management/31_list_group_users.py")
        elif choice == "5":
            run_script("4_scraping/41_scrape_links_advanced.py")
        elif choice == "6":
            run_script("5_monitoring/50_group_stats.py")
        elif choice == "7":
            run_script("run.py", cwd="6_messaging/64_claude_edition")
        elif choice == "8":
            run_dashboard_pair(cwd="6_messaging/65")
        elif choice == "11":
            run_script("7_utilities/71_find_my_participation.py")
        elif choice == "12":
            run_script("7_utilities/70_purge_my_messages.py")
        elif choice == "0":
            console.print(Panel(Text("Goodbye!", justify="center", style="bold green"), border_style="green"))
            break
        else:
            console.print("[bold red]❌ Invalid choice.[/bold red]")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold red]⛔ Manager closed. Exiting...[/bold red]")
        sys.exit(0)
