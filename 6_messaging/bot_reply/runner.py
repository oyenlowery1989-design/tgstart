# 6_messaging/bot_reply/runner.py
"""Bot Reply runner: one asyncio loop running two Telethon clients — a userbot that
drafts and (once approved) sends replies, and an approval bot that DMs the operator
Approve/Edit/Reject buttons. Config and the pending-reply queue live in bot_reply.db,
hot-reloaded via the same config_bump polling pattern as 6_messaging/65/ghost_runner.py."""
import asyncio
import os
import sys
from pathlib import Path
from typing import Awaitable, Callable, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from telethon import TelegramClient, events

import db
import trigger
import persona as persona_mod
import providers
from dashboard.state import session_path

API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))

DEFAULT_TTL_HOURS = 6.0
DEFAULT_HISTORY_DEPTH = 10
CONFIG_POLL_INTERVAL = 2
APPROVED_POLL_INTERVAL = 2
EXPIRY_SWEEP_INTERVAL = 300

# Set by Task 6 once the approval bot client exists. Left as a no-op here so this module
# is independently runnable/testable before Task 6 is implemented.
notify_approval_bot: Callable[[int], Awaitable[None]] = None


def build_globals(conn) -> trigger.GlobalSettings:
    return trigger.GlobalSettings(
        trigger_mode=db.get_setting(conn, "trigger_mode", "mentions"),
        small_group_max_size=int(db.get_setting(conn, "small_group_max_size", "50")),
    )


def build_chat_config(conn, chat_id: int, member_count: Optional[int]) -> trigger.ChatConfig:
    row = db.get_chat_config(conn, chat_id)
    if row is None:
        return trigger.ChatConfig(enabled=False, member_count=member_count)
    return trigger.ChatConfig(
        enabled=bool(row["enabled"]),
        trigger_mode=row["trigger_mode"],
        member_count=member_count,
    )


async def handle_new_message(event, conn, provider_fn, me_id: int) -> None:
    chat = await event.get_chat()
    chat_id = event.chat_id
    sender = await event.get_sender()
    sender_id = getattr(sender, "id", None)
    text = event.raw_text or ""

    member_count = getattr(chat, "participants_count", None)
    chat_cfg = build_chat_config(conn, chat_id, member_count)
    globals_ = build_globals(conn)

    is_mention = f"@{(await event.client.get_me()).username or ''}" in text if text else False
    reply_to = await event.get_reply_message() if event.is_reply else None
    is_reply_to_operator = bool(reply_to and reply_to.sender_id == me_id)

    msg_meta = trigger.MessageMeta(
        is_own_message=(sender_id == me_id),
        is_from_bot=bool(getattr(sender, "bot", False)),
        is_mention=is_mention,
        is_reply_to_operator=is_reply_to_operator,
    )

    if not trigger.should_reply(chat_cfg, globals_, msg_meta):
        return

    row = db.get_chat_config(conn, chat_id) or {}
    persona_text = persona_mod.load_persona(row.get("persona_override"))

    history_depth = int(db.get_setting(conn, "history_depth", str(DEFAULT_HISTORY_DEPTH)))
    history = []
    async for hist_msg in event.client.iter_messages(chat_id, limit=history_depth):
        if hist_msg.id == event.id:
            continue
        hist_sender = await hist_msg.get_sender()
        name = getattr(hist_sender, "first_name", None) or getattr(hist_sender, "username", None) or "unknown"
        history.append({"sender": name, "text": hist_msg.raw_text or ""})
    history.reverse()

    try:
        draft = await provider_fn(persona_text, history, text)
    except Exception as e:
        # Drafting failures are logged, not queued — nothing to approve/reject yet.
        print(f"[bot_reply] draft failed for chat {chat_id}: {e}", file=sys.stderr)
        return

    if not draft:
        return

    chat_title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or str(chat_id)
    sender_name = getattr(sender, "first_name", None) or getattr(sender, "username", None) or str(sender_id)
    reply_id = db.insert_pending_reply(
        conn, chat_id=chat_id, chat_title=chat_title, source_message_id=event.id,
        source_text=text, source_sender=sender_name, draft_text=draft,
    )
    if reply_id is None:
        return  # duplicate event for a message we've already drafted

    if notify_approval_bot is not None:
        await notify_approval_bot(reply_id)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(handle_new_message)
    assert callable(build_globals) and callable(build_chat_config)
    print("runner.py (drafting half) smoke check OK — signatures present")
