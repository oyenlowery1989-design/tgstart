"""Group analytics, extracted from 5_monitoring/50_group_stats.py."""
import csv
from collections import Counter
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional, Tuple

from telethon.tl.types import Message

from dashboard.state import ROOT_DIR
from dashboard.tg_client import make_client
from utils.tg_utils import slugify

ProgressCB = Callable[[int, int, str], Awaitable[None]]


@dataclass
class StatsResult:
    total_scanned: int
    top_users: List[Tuple[str, int, float]]
    peak_hours: List[Tuple[int, int]]
    csv_path: str


async def group_stats(session_name: str, group_id: int, limit: int = 2000,
                       progress_cb: Optional[ProgressCB] = None) -> StatsResult:
    client = make_client(session_name)
    await client.start()
    try:
        entity = await client.get_entity(group_id)
        user_msgs: Counter = Counter()
        user_names = {}
        hours: Counter = Counter()
        total_scanned = 0

        async for msg in client.iter_messages(entity, limit=limit):
            if not isinstance(msg, Message):
                continue
            total_scanned += 1
            if msg.sender_id:
                user_msgs[msg.sender_id] += 1
                if msg.sender_id not in user_names:
                    sender = getattr(msg, "sender", None)
                    if sender:
                        name = f"@{sender.username}" if getattr(sender, "username", None) else \
                            f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip()
                        user_names[msg.sender_id] = name or f"ID:{msg.sender_id}"
            if msg.date:
                hours[msg.date.hour] += 1
            if progress_cb:
                await progress_cb(total_scanned, limit, f"Scanned {total_scanned} messages...")

        top_users = [
            (user_names.get(uid, str(uid)), count, (count / total_scanned) * 100 if total_scanned else 0.0)
            for uid, count in user_msgs.most_common(10)
        ]
        peak_hours = sorted(hours.most_common(5))

        csv_path = _save_csv(entity, total_scanned, user_msgs, user_names, hours)
        return StatsResult(total_scanned=total_scanned, top_users=top_users, peak_hours=peak_hours, csv_path=csv_path)
    finally:
        await client.disconnect()


def _save_csv(entity, total_scanned, user_msgs, user_names, hours) -> str:
    out_dir = ROOT_DIR / "5_monitoring" / "50_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify(getattr(entity, "title", ""))
    safe_id = str(entity.id).replace("-", "n")
    out_csv = out_dir / f"stats_{safe_name}_{safe_id}.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value", "Count/Details"])
        writer.writerow(["GROUP_TITLE", getattr(entity, "title", "N/A"), str(entity.id)])
        writer.writerow(["SCAN_TOTAL", str(total_scanned), ""])
        writer.writerow([])
        writer.writerow(["TOP_USERS"])
        for uid, count in user_msgs.most_common(50):
            writer.writerow(["User", user_names.get(uid, str(uid)), str(count)])
        writer.writerow([])
        writer.writerow(["HOURLY_ACTIVITY"])
        for hr in range(24):
            writer.writerow(["Hour", f"{hr:02}:00", str(hours[hr])])
    return str(out_csv)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(group_stats)
    print("stats_service.py smoke check OK")
