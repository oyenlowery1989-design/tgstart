
"""
FILE: src/core/logger.py
PURPOSE: Defines setup_logger, log_error, and log_to_disk functions.
IMPROVEMENTS: Maintains a rolling log rotation (30 days) and separate directories for cleaner data storage.
"""
import os
import sys
import json
import logging
import traceback
from datetime import datetime
from rich.console import Console
from zoneinfo import ZoneInfo
from src.config.settings import TIMEZONE_STR, MAX_LOG_AGE_DAYS

# --- Setup ---
try:
    target_tz = ZoneInfo(TIMEZONE_STR)
except Exception:
    target_tz = ZoneInfo("UTC")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

console = Console()

def get_now():
    """Returns awareness datetime in configured timezone."""
    return datetime.now(target_tz)

def ensure_log_dirs():
    """Creates necessary directories."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

# --- Logic ---

def log_error(error_type, error_msg, stack_trace=None):
    """
    Logs structured errors to both console (red) and disk (JSONL).
    """
    ts = get_now().isoformat()
    entry = {
        "ts": ts,
        "type": error_type,
        "msg": error_msg,
        "stack": stack_trace
    }
    
    # Console Output
    console.print(f"[bold red]❌ ERROR ({error_type}):[/bold red] {error_msg}")
    if stack_trace:
        # Only show last line of stack trace to keep console clean
        last_line = stack_trace.strip().split('\n')[-1]
        console.print(f"[dim]{last_line}[/dim]")
    
    # Disk Output
    try:
        err_file = os.path.join(LOGS_DIR, "errors.jsonl")
        with open(err_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"FATAL: Could not write to error log: {e}")

def log_to_disk(event_type, payload):
    """
    Logs operational events (joins, messages, etc.) to a daily log file.
    """
    ts = get_now()
    date_str = ts.strftime("%m.%d.%Y")
    filename = f"{date_str}.jsonl"
    filepath = os.path.join(LOGS_DIR, filename)
    
    entry = {
        "ts": ts.isoformat(),
        "type": event_type,
        "data": payload
    }
    
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        console.print(f"[red]Failed to log event:[/red] {e}")

def rotate_old_logs():
    """
    Deletes log files older than MAX_LOG_AGE_DAYS.
    """
    now = get_now()
    deleted_count = 0
    
    if not os.path.exists(LOGS_DIR):
        return
        
    for f in os.listdir(LOGS_DIR):
        if not f.endswith(".jsonl"): continue
        path = os.path.join(LOGS_DIR, f)
        
        try:
            stat = os.stat(path)
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=target_tz)
            age_days = (now - mtime).days
            
            if age_days > MAX_LOG_AGE_DAYS:
                os.remove(path)
                deleted_count += 1
        except Exception:
            continue
            
    if deleted_count > 0:
        console.print(f"[yellow]🧹 Cleaned up {deleted_count} old log files.[/yellow]")
