"""Link scraper, extracted from 4_scraping/41_scrape_links_advanced.py."""
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Dict, Iterable, List, Optional

from telethon.tl.types import Message, MessageEntityTextUrl

from dashboard.state import ROOT_DIR
from dashboard.tg_client import make_client
from utils.tg_utils import slugify

ProgressCB = Callable[[int, int, str], Awaitable[None]]

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
INVISIBLES = ["​", "‌", "‍", "﻿", "⁠"]


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


@dataclass
class ScrapeResult:
    scanned: int
    links: List[LinkRecord]
    csv_path: str
    oldest_reached: Optional[str]


def _repair_url(u: str) -> str:
    s = (u or "").strip()
    for ch in INVISIBLES:
        s = s.replace(ch, "")
    s = s.strip().rstrip(").,!?;:\"'<>]")
    low = s.lower()
    if low.startswith("//"):
        s = "https:" + s
    elif low.startswith("tps://"):
        s = "h" + s
    elif low.startswith("hxxps://"):
        s = "https://" + s[8:]
    elif low.startswith("hxxp://"):
        s = "http://" + s[7:]
    elif low.startswith("www."):
        s = "https://" + s
    return s


def _passes_filter(url: str, keyword_lower: str, startswith: Optional[str]) -> bool:
    if startswith and not url.startswith(startswith):
        return False
    if keyword_lower and keyword_lower not in url.lower():
        return False
    return True


def _parse_since_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_topic_id(msg: Message) -> Optional[int]:
    rt = getattr(msg, "reply_to", None)
    if not rt:
        return None
    return getattr(rt, "reply_to_top_id", None) or getattr(rt, "top_msg_id", None) or None


def _urls_from_text_urls(msg: Message) -> Iterable[str]:
    if not msg.entities:
        return
    for ent in msg.entities:
        if isinstance(ent, MessageEntityTextUrl):
            yield _repair_url(str(ent.url))


def _urls_from_regex(text: str) -> Iterable[str]:
    for m in URL_RE.finditer(text or ""):
        yield _repair_url(m.group(1))


def _checkpoint_path(out_dir: Path, group_id: int) -> Path:
    return out_dir / "checkpoints" / f"checkpoint_{str(group_id).replace('-', 'n')}.json"


def _next_available_filename(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        cand = parent / f"{stem}({i}){suffix}"
        if not cand.exists():
            return cand
        i += 1


async def scrape_links(session_name: str, group_id: int, keyword: Optional[str] = None,
                        startswith: Optional[str] = None, since_date: Optional[str] = None,
                        message_limit: Optional[int] = 500, resume: bool = False,
                        progress_cb: Optional[ProgressCB] = None) -> ScrapeResult:
    keyword_lower = (keyword or "").lower()
    since_dt = _parse_since_date(since_date)
    seen: Dict[str, LinkRecord] = {}
    scanned = 0
    oldest_dt_seen = None

    out_dir = ROOT_DIR / "4_scraping" / "41_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = _checkpoint_path(out_dir, group_id)

    client = make_client(session_name)
    await client.start()
    last_id_scanned = 0
    try:
        entity = await client.get_entity(group_id)
        offset_id = 0
        if resume and checkpoint_path.exists():
            data = json.loads(checkpoint_path.read_text())
            offset_id = data.get("last_id", 0)
        last_id_scanned = offset_id

        async for msg in client.iter_messages(entity, limit=message_limit, offset_id=offset_id):
            if not isinstance(msg, Message):
                continue
            last_id_scanned = msg.id
            scanned += 1
            if progress_cb:
                await progress_cb(scanned, message_limit or 0, f"Found {len(seen)} links... ({scanned} msgs)")
            msg_dt = msg.date
            if msg_dt and msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)
            msg_dt = (msg_dt or datetime.now(timezone.utc)).astimezone(timezone.utc)
            if since_dt and msg_dt < since_dt:
                break
            oldest_dt_seen = msg_dt
            topic_id = _get_topic_id(msg)
            text = msg.raw_text or msg.message or ""
            sender = getattr(msg, "sender", None)
            user_id = getattr(sender, "id", None) if sender else None
            username = getattr(sender, "username", None) if sender else None
            first_name = getattr(sender, "first_name", None) if sender else None
            last_name = getattr(sender, "last_name", None) if sender else None

            for url in list(_urls_from_text_urls(msg)) + list(_urls_from_regex(text)):
                if url and _passes_filter(url, keyword_lower, startswith) and url not in seen:
                    seen[url] = LinkRecord(
                        url=url, date_dt=msg_dt, message_id=msg.id, topic_id=topic_id,
                        user_id=user_id, username=username, user_first=first_name, user_last=last_name,
                        group_name=getattr(entity, "title", "N/A"), group_id=entity.id,
                    )

        csv_path = _save_csv(seen, out_dir, getattr(entity, "title", "N/A"), entity.id)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        return ScrapeResult(scanned=scanned, links=list(seen.values()), csv_path=csv_path,
                             oldest_reached=oldest_dt_seen.isoformat() if oldest_dt_seen else None)
    except Exception:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps({"last_id": last_id_scanned}))
        raise
    finally:
        await client.disconnect()


def _save_csv(seen: Dict[str, LinkRecord], out_dir: Path, group_name: str, group_id: int) -> str:
    safe_name = slugify(group_name)
    safe_id = str(group_id).replace("-", "n")
    base_path = out_dir / f"41_links_{safe_name}_{safe_id}.csv"
    out_csv = _next_available_filename(base_path)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group_name", "group_id", "url", "date_sent", "message_id", "topic_id", "user_id", "username", "first_name", "last_name"])
        for r in seen.values():
            w.writerow([r.group_name, r.group_id, r.url, r.date_dt.isoformat(), r.message_id, r.topic_id, r.user_id, r.username, r.user_first, r.user_last])
    return str(out_csv)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(scrape_links)
    sig = inspect.signature(scrape_links)
    assert list(sig.parameters.keys())[:2] == ["session_name", "group_id"]
    print("scrape_service.py smoke check OK")
