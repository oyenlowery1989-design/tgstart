#!/usr/bin/env python3
"""
40_scrape_links.py

Extracts filtered links from a Telegram group or channel
using a logged-in Telegram *user* account (Telethon).

Run:
    python 40_scrape_links.py
"""

import asyncio
import csv
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
from telethon.tl.types import Message

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ui_utils import console, print_header, print_success


# ============================================================
# ======================= CONFIG =============================
# ============================================================

from dotenv import load_dotenv
load_dotenv()

# Telegram API credentials
API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Session name (reuses existing session if present)
SESSION_NAME = os.getenv("DEFAULT_SESSION", os.path.join(ROOT_DIR, "sessions", "americandreamer8"))

# If it's a relative path, make it absolute relative to ROOT_DIR
if not os.path.isabs(SESSION_NAME):
    SESSION_NAME = os.path.join(ROOT_DIR, SESSION_NAME)

# Target group / channel
# Examples:
#   -1001234567890
#   "@somepublicchannel"
#   "somepublicchannel"
TARGET = "1623947149"

# Link filtering
KEYWORD = "lobstr.co/trade"            # case-insensitive substring match
STARTSWITH = None             # e.g. "https://lobstr.co/" or None

# History limits
SINCE_DATE = "2026-02-02"             # e.g. "2026-01-01" or None
MESSAGE_LIMIT = None          # e.g. 20000 or None

# Output ordering: "desc" (newest → oldest) or "asc"
ORDER = "desc"

# Progress logging
PRINT_PROGRESS = True
PROGRESS_EVERY = 2000

# Output files
OUT_CSV = "30_links.csv"

# ============================================================


URL_RE = re.compile(
    r"""(?ix)\b(https?://[^\s<>"']+|www\.[^\s<>"']+)"""
)


@dataclass(frozen=True)
class LinkRecord:
    url: str
    date_sent: str
    message_id: int


def normalize_url(url: str) -> str:
    url = url.strip().rstrip(").,!?;:\"'<>]")
    if url.lower().startswith("www."):
        url = "https://" + url
    return url


def extract_urls(text: str) -> Iterable[str]:
    for m in URL_RE.finditer(text or ""):
        yield normalize_url(m.group(1))


def passes_filter(url: str) -> bool:
    if STARTSWITH and not url.startswith(STARTSWITH):
        return False
    if KEYWORD and KEYWORD.lower() not in url.lower():
        return False
    return True


def parse_since_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def ensure_login(client: TelegramClient) -> None:
    await client.connect()
    if await client.is_user_authorized():
        return

    phone = input("Phone number (+countrycode...): ").strip()
    sent = await client.send_code_request(phone)
    code = input("Login code from Telegram: ").strip()

    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
    except SessionPasswordNeededError:
        pw = input("2FA password: ").strip()
        await client.sign_in(password=pw)


async def resolve_entity(client: TelegramClient):
    t = TARGET.strip()
    if t.startswith("@"):
        t = t[1:]
    if re.fullmatch(r"-?\d+", t):
        return await client.get_entity(int(t))
    return await client.get_entity(t)


async def scan_links(client, entity) -> Dict[str, LinkRecord]:
    seen: Dict[str, LinkRecord] = {}
    scanned = 0
    since_dt = parse_since_date(SINCE_DATE)

    async for msg in client.iter_messages(entity, limit=MESSAGE_LIMIT):
        scanned += 1

        if PRINT_PROGRESS and scanned % PROGRESS_EVERY == 0:
            console.print(f"Scanned {scanned:,} messages | Links: {len(seen):,}")

        if not isinstance(msg, Message) or not msg.message:
            continue

        msg_dt = msg.date
        if msg_dt and msg_dt.tzinfo is None:
            msg_dt = msg_dt.replace(tzinfo=timezone.utc)

        if since_dt and msg_dt and msg_dt < since_dt:
            break

        for url in extract_urls(msg.message):
            if not passes_filter(url):
                continue
            if url in seen:
                continue

            seen[url] = LinkRecord(
                url=url,
                date_sent=(msg_dt or datetime.now(timezone.utc)).isoformat(),
                message_id=msg.id,
            )

    return seen


def write_outputs(records):
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["url", "date_sent", "message_id"])
        for r in records:
            w.writerow([r.url, r.date_sent, r.message_id])


async def main():
    print_header("Scrape Links")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await ensure_login(client)

    entity = await resolve_entity(client)
    console.print(f"Scanning: {getattr(entity, 'title', None) or TARGET}")

    seen = await scan_links(client, entity)

    records = list(seen.values())
    records.sort(
        key=lambda r: r.date_sent,
        reverse=(ORDER == "desc"),
    )

    write_outputs(records)

    print_success(f"Saved {len(records):,} unique links to {OUT_CSV}")

    await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        console.print("\n⛔ Process cancelled by user. Exiting safely...")
        sys.exit(0)
