#!/usr/bin/env python3
"""
Advanced Link Scraper

A robust link extraction tool that scrapes URLs from a target chat.
Features:
- Checkpointing (resumes where it left off)
- Link filtering (keywords, start patterns)
- Duplicate detection
- Output to CSV with detailed metadata
- Date cutoffs
"""
import asyncio
import csv
import re
import time
import os
import sys
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Iterable, List

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
from telethon.tl import functions
from telethon.tl.types import Message, MessageEntityTextUrl

from dotenv import load_dotenv

# Add parent directory to path so we can find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import ui_utils, tg_utils
from utils.ui_utils import console

# Load environment variables
load_dotenv()

# ======================= CONFIG =======================
API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_NAME = os.getenv("DEFAULT_SESSION", os.path.join(ROOT_DIR, "sessions", "TonkinStuart"))

# If it's a relative path, make it absolute relative to ROOT_DIR
if not os.path.isabs(SESSION_NAME):
    SESSION_NAME = os.path.join(ROOT_DIR, SESSION_NAME)

TARGET = "1623947149"   # or -100...

KEYWORD = None              # case-insensitive substring match
STARTSWITH = None               # e.g. "https://lobstr.co/" or None

SINCE_DATE = None               # e.g. "2026-02-02" or None
MESSAGE_LIMIT = 500            # Limit to 500 for a quick test

OUTPUT_MODE = "found"           # "found" or "sorted"
SORT_ORDER = "desc"             # used only when OUTPUT_MODE="sorted"

PRINT_PROGRESS = True
PROGRESS_EVERY = 8000

OUT_DIR = "41_data"
OUT_CSV = os.path.join(OUT_DIR, "41_links.csv")
CHECKPOINT_DIR = os.path.join(OUT_DIR, "checkpoints")

# Regex finds visible URLs
URL_RE = re.compile(
    r"""(?ix)
    \b(
        https?://[^\s<>"'()\[\]]+
        |
        www\.[^\s<>"'()\[\]]+
        |
        //[^ \t\r\n<>"'()\[\]]+
    )
    """
)

INVISIBLES = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]

@dataclass(frozen=True)
class LinkRecord:
    url: str
    date_dt: datetime
    message_id: int
    topic_id: Optional[int]
    user_id: Optional[int]
    username: Optional[str]
    user_first: Optional[str]
    user_last: Optional[str]
    group_name: str
    group_id: int

def next_available_filename(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return path
    stem, suffix, parent = p.stem, p.suffix, p.parent
    i = 1
    while True:
        cand = parent / f"{stem}({i}){suffix}"
        if not cand.exists():
            return str(cand)
        i += 1

def repair_url(u: str) -> str:
    s = (u or "").strip()
    for ch in INVISIBLES:
        s = s.replace(ch, "")
    s = s.strip().rstrip(").,!?;:\"'<>]")
    low = s.lower()
    if low.startswith("//"): s = "https:" + s
    elif low.startswith("tps://"): s = "h" + s
    elif low.startswith("hxxps://"): s = "https://" + s[8:]
    elif low.startswith("hxxp://"): s = "http://" + s[7:]
    elif low.startswith("www."): s = "https://" + s
    return s

def passes_filter(url: str, keyword_lower: str) -> bool:
    if STARTSWITH and not url.startswith(STARTSWITH): return False
    if keyword_lower and keyword_lower not in url.lower(): return False
    return True

def parse_since_date(s: Optional[str]) -> Optional[datetime]:
    if not s: return None
    s = s.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    if s.endswith("Z"): s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def fmt_dt(dt: Optional[datetime]) -> str:
    if not dt: return "n/a"
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()

def get_topic_id(msg: Message) -> Optional[int]:
    rt = getattr(msg, "reply_to", None)
    if not rt: return None
    return getattr(rt, "reply_to_top_id", None) or getattr(rt, "top_msg_id", None) or None

def urls_from_text_urls(msg: Message) -> Iterable[str]:
    if not msg.entities: return
    for ent in msg.entities:
        if isinstance(ent, MessageEntityTextUrl): yield repair_url(str(ent.url))

def urls_from_regex(text: str) -> Iterable[str]:
    for m in URL_RE.finditer(text or ""): yield repair_url(m.group(1))

async def ensure_login(client: TelegramClient) -> None:
    await client.connect()
    if await client.is_user_authorized(): return
    phone = console.input("[cyan]Phone number (+countrycode...): [/cyan]").strip()
    sent = await client.send_code_request(phone)
    code = console.input("[cyan]Login code from Telegram: [/cyan]").strip()
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
    except SessionPasswordNeededError:
        pw = console.input("[yellow]2FA password: [/yellow]").strip()
        await client.sign_in(password=pw)

async def try_get_total_count(client: TelegramClient, entity) -> Optional[int]:
    try:
        res = await client(functions.messages.GetHistoryRequest(
            peer=entity, offset_id=0, offset_date=None, add_offset=0, limit=0, max_id=0, min_id=0, hash=0
        ))
        return getattr(res, "count", None)
    except Exception: return None

def build_output_rows(seen: Dict[str, LinkRecord]) -> List[LinkRecord]:
    records = list(seen.values())
    if OUTPUT_MODE == "found": return records
    reverse = (SORT_ORDER == "desc")
    records.sort(key=lambda r: (r.date_dt, r.message_id), reverse=reverse)
    return records

def save_csv(seen: Dict[str, LinkRecord], reason: str, group_name: str, group_id: int) -> None:
    if not os.path.exists(OUT_DIR): os.makedirs(OUT_DIR)
    
    safe_name = tg_utils.slugify(group_name)
    safe_id = str(group_id).replace("-", "n")
    base_path = os.path.join(OUT_DIR, f"41_links_{safe_name}_{safe_id}.csv")
    
    out_csv = next_available_filename(base_path)
    records = build_output_rows(seen)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group_name", "group_id", "url", "date_sent", "message_id", "topic_id", "user_id", "username", "first_name", "last_name"])
        for r in records:
            w.writerow([r.group_name, r.group_id, r.url, r.date_dt.isoformat(), r.message_id, r.topic_id, r.user_id, r.username, r.user_first, r.user_last])
    console.print(f"\n[bold green]Saved {len(records):,} unique links ({reason}).[/bold green]")
    console.print(f"- [dim]{out_csv}[/dim]")

async def main():
    keyword_lower = (KEYWORD or "").lower()
    since_dt = parse_since_date(SINCE_DATE)
    seen: Dict[str, LinkRecord] = {}
    scanned = 0
    newest_dt_seen = None
    oldest_dt_seen = None
    start_ts = time.time()

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try:
        await ensure_login(client)
        entity = await tg_utils.pick_target(client, TARGET)
        if not entity:
            ui_utils.print_error("No target selected. Exiting.")
            return

        title = getattr(entity, "title", None) or TARGET
        ui_utils.print_header(f"Scanning: {title}")
        if since_dt: console.print(f"[yellow]SINCE_DATE cutoff: {fmt_dt(since_dt)}[/yellow]")
        total_count = await try_get_total_count(client, entity)
        if total_count: console.print(f"[blue]Approx total messages: {total_count:,}[/blue]")
        else: console.print("[dim]Approx total messages: (not available)[/dim]")

        # --- Checkpoint Logic ---
        checkpoint_name = f"checkpoint_{str(entity.id).replace('-', 'n')}.json"
        checkpoint_path = os.path.join(CHECKPOINT_DIR, checkpoint_name)
        offset_id = 0
        if os.path.exists(checkpoint_path):
            try:
                with open(checkpoint_path, "r") as f:
                    data = json.load(f)
                    last_id = data.get("last_id")
                    if last_id:
                        console.print(f"\n[bold yellow]📂 Found checkpoint! Stopped at message ID: {last_id}[/bold yellow]")
                        choice = console.input("👉 Resume from here? (y/n): ").strip().lower()
                        if choice == 'y':
                            offset_id = last_id
                            console.print(f"🚀 Resuming from ID: {offset_id}...")
            except (json.JSONDecodeError, OSError, KeyError) as e:
                console.print(f"[dim]Ignoring unreadable checkpoint file: {e}[/dim]")
        last_id_scanned = offset_id

        with ui_utils.get_progress() as progress:
            task_limit = MESSAGE_LIMIT or total_count or 1000000
            task = progress.add_task(f"Extracting links...", total=task_limit)
            async for msg in client.iter_messages(entity, limit=MESSAGE_LIMIT, offset_id=offset_id):
                if not isinstance(msg, Message): continue
                last_id_scanned = msg.id
                scanned += 1
                progress.update(task, advance=1, description=f"Found [bold green]{len(seen)}[/bold green] links... [dim]({scanned:,} msg)[/dim]")
                msg_dt = msg.date
                if msg_dt and msg_dt.tzinfo is None: msg_dt = msg_dt.replace(tzinfo=timezone.utc)
                msg_dt = (msg_dt or datetime.now(timezone.utc)).astimezone(timezone.utc)
                if since_dt and msg_dt < since_dt:
                    console.print(f"\n[bold yellow]Reached SINCE_DATE cutoff: {fmt_dt(msg_dt)}[/bold yellow]")
                    break
                if newest_dt_seen is None: newest_dt_seen = msg_dt
                oldest_dt_seen = msg_dt
                topic_id = get_topic_id(msg)
                text = (msg.raw_text or msg.message or "")
                sender = getattr(msg, "sender", None)
                user_id = getattr(sender, "id", None) if sender else None
                username = getattr(sender, "username", None) if sender else None
                first_name = getattr(sender, "first_name", None) if sender else None
                last_name = getattr(sender, "last_name", None) if sender else None

                for url in urls_from_text_urls(msg):
                    if url and passes_filter(url, keyword_lower) and url not in seen:
                        seen[url] = LinkRecord(
                            url=url, date_dt=msg_dt, message_id=msg.id, 
                            topic_id=topic_id, user_id=user_id, username=username, 
                            user_first=first_name, user_last=last_name,
                            group_name=getattr(entity, 'title', 'N/A'),
                            group_id=entity.id
                        )
                if text:
                    tl = text.lower()
                    if any(x in tl for x in ["http", "www.", "//", "hxxp", "tps://"]):
                        for url in urls_from_regex(text):
                            if url and passes_filter(url, keyword_lower) and url not in seen:
                                seen[url] = LinkRecord(
                                    url=url, date_dt=msg_dt, message_id=msg.id, 
                                    topic_id=topic_id, user_id=user_id, username=username, 
                                    user_first=first_name, user_last=last_name,
                                    group_name=getattr(entity, 'title', 'N/A'),
                                    group_id=entity.id
                                )

        ui_utils.print_success("Finished Scanning!")
        console.print(f"  Messages scanned: [bold]{scanned:,}[/bold]")
        console.print(f"  Unique links found: [bold cyan]{len(seen):,}[/bold cyan]")
        console.print(f"  Oldest reached: [dim]{fmt_dt(oldest_dt_seen)}[/dim]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n\n⛔ Interrupted/Cancelled. Saving partial results...")
        save_csv(seen, "interrupted", getattr(entity, 'title', 'N/A'), entity.id)
        if not os.path.exists(CHECKPOINT_DIR): os.makedirs(CHECKPOINT_DIR)
        with open(checkpoint_path, "w") as f: json.dump({"last_id": last_id_scanned, "timestamp": time.time()}, f)
        console.print(f"💾 Checkpoint saved: [dim]{checkpoint_path}[/dim]")
    except Exception as e:
        ui_utils.print_error(str(e))
        save_csv(seen, "error", getattr(entity, 'title', 'N/A'), entity.id)
        if not os.path.exists(CHECKPOINT_DIR): os.makedirs(CHECKPOINT_DIR)
        with open(checkpoint_path, "w") as f: json.dump({"last_id": last_id_scanned, "timestamp": time.time()}, f)
    else:
        save_csv(seen, "completed", getattr(entity, 'title', 'N/A'), entity.id)
        if os.path.exists(checkpoint_path): os.remove(checkpoint_path)
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, EOFError): sys.exit(0)
