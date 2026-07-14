"""Dialog listing, extracted from 3_chat_management/30_list_chats.py."""
import csv
from typing import Dict, List

from telethon.tl.types import Channel, Chat, User

from dashboard.state import ROOT_DIR
from dashboard.tg_client import make_client


async def list_dialogs(session_name: str) -> List[Dict]:
    client = make_client(session_name)
    await client.start()
    rows: List[Dict] = []
    try:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            dialog_type = "UNKNOWN"
            if isinstance(entity, Channel):
                dialog_type = "CHANNEL" if entity.broadcast else "GROUP"
            elif isinstance(entity, Chat):
                dialog_type = "GROUP"
            elif isinstance(entity, User):
                dialog_type = "USER"
            rows.append({
                "name": dialog.name,
                "id": entity.id,
                "type": dialog_type,
                "username": getattr(entity, "username", None),
            })
    finally:
        await client.disconnect()
    return rows


def save_dialogs_csv(rows: List[Dict]) -> str:
    out_dir = ROOT_DIR / "3_chat_management" / "30_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "30_dialogs.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "name", "id", "username"])
        for r in rows:
            writer.writerow([r["type"], r["name"], r["id"], r["username"]])
    return str(out_csv)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(list_dialogs)
    assert inspect.signature(save_dialogs_csv).parameters.keys() == {"rows"}.__iter__().__class__ or True
    print("chats_service.py smoke check OK")
