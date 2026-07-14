"""Self-message purge, extracted from 7_utilities/70_purge_my_messages.py."""
import asyncio
from typing import Awaitable, Callable, Dict, List, Optional

from telethon import types

from dashboard.tg_client import make_client

ProgressCB = Callable[[int, int, str], Awaitable[None]]


async def scan_my_activity(session_name: str, progress_cb: Optional[ProgressCB] = None) -> List[Dict]:
    client = make_client(session_name)
    await client.start()
    active_chats: List[Dict] = []
    try:
        dialogs = [d async for d in client.iter_dialogs(limit=100)]
        for i, dialog in enumerate(dialogs, 1):
            entity = dialog.entity
            if not isinstance(entity, (types.Channel, types.Chat)):
                continue
            if progress_cb:
                await progress_cb(i, len(dialogs), f"Checking: {dialog.name}")
            try:
                history = await client.get_messages(entity, from_user="me", limit=1)
                if history:
                    total = (await client.get_messages(entity, from_user="me", limit=0)).total
                    active_chats.append({
                        "name": dialog.name, "id": entity.id, "count": total,
                        "type": "CHANNEL" if getattr(entity, "broadcast", False) else "GROUP",
                    })
            except Exception:
                continue
        active_chats.sort(key=lambda x: x["count"], reverse=True)
        if progress_cb:
            await progress_cb(len(dialogs), len(dialogs), "Done")
    finally:
        await client.disconnect()
    return active_chats


async def preview_my_messages(session_name: str, group_id: int, limit: int = 10) -> List[Dict]:
    client = make_client(session_name)
    await client.start()
    rows: List[Dict] = []
    try:
        async for msg in client.iter_messages(group_id, from_user="me", limit=limit):
            content = (msg.text[:50] + "...") if msg.text else "[Media/Sticker]"
            rows.append({"date": msg.date.strftime("%Y-%m-%d %H:%M"), "content": content})
    finally:
        await client.disconnect()
    return rows


async def purge_my_messages(session_name: str, group_id: int, target_name: str, confirm_name: str,
                             progress_cb: Optional[ProgressCB] = None) -> Dict:
    # Safety-critical: this check MUST happen before any Telethon client is created or
    # connected, so a mismatched confirmation can never touch the network or a message.
    if confirm_name.strip() != target_name.strip():
        raise ValueError("Confirmation text does not match the target chat name. Purge aborted.")

    client = make_client(session_name)
    await client.start()
    deleted_count = 0
    try:
        while True:
            ids_to_delete = [msg.id async for msg in client.iter_messages(group_id, from_user="me", limit=100)]
            if not ids_to_delete:
                break
            await client.delete_messages(group_id, ids_to_delete)
            deleted_count += len(ids_to_delete)
            if progress_cb:
                await progress_cb(deleted_count, 0, f"Deleted {deleted_count} messages so far...")
            await asyncio.sleep(1)
        if progress_cb:
            await progress_cb(deleted_count, deleted_count, f"Done. Deleted {deleted_count} messages.")
    finally:
        await client.disconnect()
    return {"deleted_count": deleted_count}


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(scan_my_activity)
    assert inspect.iscoroutinefunction(preview_my_messages)
    assert inspect.iscoroutinefunction(purge_my_messages)
    sig = inspect.signature(purge_my_messages)
    assert "confirm_name" in sig.parameters and "target_name" in sig.parameters
    print("purge_service.py smoke check OK")
