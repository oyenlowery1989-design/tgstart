"""Session listing/verification, extracted from 2_verify/2_verify_login_advanced.py."""
from typing import Awaitable, Callable, Dict, List, Optional

from telethon import TelegramClient

from dashboard.state import list_sessions, session_path
from dashboard.tg_client import API_ID, API_HASH

ProgressCB = Callable[[int, int, str], Awaitable[None]]


async def check_session(session_name: str) -> Dict[str, str]:
    client = TelegramClient(session_path(session_name), API_ID, API_HASH)
    status = "UNKNOWN"
    details = ""
    try:
        await client.connect()
        if not await client.is_user_authorized():
            status = "INVALID"
            details = "Revoked or expired"
        else:
            me = await client.get_me()
            status = "ACTIVE"
            user_display = f"@{me.username}" if me.username else f"{me.first_name} {me.last_name or ''}".strip()
            details = f"{user_display} (ID: {me.id})"
    except Exception as e:
        status = "ERROR"
        details = str(e)
    finally:
        await client.disconnect()
    return {"name": session_name, "status": status, "details": details}


async def check_all_sessions(progress_cb: Optional[ProgressCB] = None) -> List[Dict[str, str]]:
    names = list_sessions()
    results: List[Dict[str, str]] = []
    for i, name in enumerate(names, 1):
        if progress_cb:
            await progress_cb(i - 1, len(names), f"Checking {name}...")
        results.append(await check_session(name))
        if progress_cb:
            await progress_cb(i, len(names), f"Checked {name}")
    return results


if __name__ == "__main__":
    import asyncio
    import inspect
    assert inspect.iscoroutinefunction(check_session)
    assert inspect.iscoroutinefunction(check_all_sessions)
    result = asyncio.run(check_all_sessions())
    print("sessions_service.py smoke check OK:", result)
