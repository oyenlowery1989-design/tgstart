"""Participation finder, extracted from 7_utilities/71_find_my_participation.py."""
from typing import Awaitable, Callable, Dict, List, Optional

from telethon import types

from dashboard.tg_client import make_client

ProgressCB = Callable[[int, int, str], Awaitable[None]]


async def find_participation(session_name: str, progress_cb: Optional[ProgressCB] = None) -> List[Dict]:
    client = make_client(session_name)
    await client.start()
    participated: List[Dict] = []
    try:
        dialogs = [d async for d in client.iter_dialogs()]
        for i, dialog in enumerate(dialogs, 1):
            entity = dialog.entity
            if not isinstance(entity, (types.Channel, types.Chat)):
                continue
            if progress_cb:
                await progress_cb(i, len(dialogs), f"Checking: {dialog.name}")
            try:
                history = await client.get_messages(entity, from_user="me", limit=1)
                if history:
                    total_from_me = await client.get_messages(entity, from_user="me", limit=0)
                    chat_type = "CHANNEL" if getattr(entity, "broadcast", False) else "GROUP"
                    participated.append({"type": chat_type, "name": dialog.name, "id": entity.id, "count": total_from_me.total})
            except Exception:
                continue
        if progress_cb:
            await progress_cb(len(dialogs), len(dialogs), "Done")
    finally:
        await client.disconnect()
    return participated


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(find_participation)
    print("participation_service.py smoke check OK")
