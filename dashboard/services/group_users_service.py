"""Group member listing, extracted from 3_chat_management/31_list_group_users.py."""
import csv
import os
from typing import Awaitable, Callable, Dict, List, Optional

from telethon.tl.types import User

from dashboard.state import ROOT_DIR
from dashboard.tg_client import make_client
from utils.tg_utils import slugify

ProgressCB = Callable[[int, int, str], Awaitable[None]]

EXPORT_PHONE_NUMBERS_DEFAULT = os.getenv("EXPORT_PHONE_NUMBERS", "false").strip().lower() == "true"
AGGRESSIVE_SCRAPE_DEFAULT = os.getenv("AGGRESSIVE_SCRAPE", "false").strip().lower() == "true"


async def list_group_users(session_name: str, group_id: int, export_phone_numbers: bool = False,
                            aggressive: bool = False, progress_cb: Optional[ProgressCB] = None) -> List[Dict]:
    client = make_client(session_name)
    await client.start()
    users: List[Dict] = []
    try:
        entity = await client.get_entity(group_id)
        async for user in client.iter_participants(entity, aggressive=aggressive):
            if not isinstance(user, User):
                continue
            users.append({
                "id": user.id,
                "username": user.username or "",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "phone": (user.phone or "") if export_phone_numbers else "",
                "bot": user.bot,
            })
            if progress_cb:
                await progress_cb(len(users), 0, f"Found {len(users)} users...")
        if progress_cb:
            await progress_cb(len(users), len(users), "Done")
    finally:
        await client.disconnect()
    return users


def save_group_users_csv(entity_title: str, entity_id: int, users: List[Dict], export_phone_numbers: bool = False) -> str:
    out_dir = ROOT_DIR / "3_chat_management" / "31_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_id = str(entity_id).replace("-", "n")
    safe_name = slugify(entity_title)
    out_csv = out_dir / f"31_users_{safe_name}_{safe_id}_{len(users)}.csv"
    header = ["group_name", "group_id", "id", "username", "first_name", "last_name"]
    if export_phone_numbers:
        header.append("phone")
    header.append("is_bot")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for u in users:
            row = [entity_title, entity_id, u["id"], u["username"], u["first_name"], u["last_name"]]
            if export_phone_numbers:
                row.append(u["phone"])
            row.append(u["bot"])
            writer.writerow(row)
    return str(out_csv)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(list_group_users)
    assert not inspect.iscoroutinefunction(save_group_users_csv)
    print("group_users_service.py smoke check OK")
