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


from telethon import Button

# Tracks in-progress "waiting for edited text" state per operator, keyed by the reply id
# the operator is currently editing. Small and short-lived (cleared once resolved), so a
# plain dict is enough — this process holds both clients, no cross-process state needed.
_pending_edits: dict = {}


def _approval_text(row: dict) -> str:
    return (
        f"**{row['chat_title']}** — {row['source_sender']}:\n"
        f"> {row['source_text']}\n\n"
        f"Draft reply:\n{row['draft_text']}"
    )


def _approval_buttons(reply_id: int):
    return [
        [Button.inline("Approve", f"approve:{reply_id}".encode()),
         Button.inline("Edit", f"edit:{reply_id}".encode()),
         Button.inline("Reject", f"reject:{reply_id}".encode())],
    ]


async def send_draft_for_approval(reply_id: int, approval_client, operator_user_id: int, conn) -> None:
    row = db.get_pending_reply(conn, reply_id)
    if row is None:
        return
    msg = await approval_client.send_message(
        operator_user_id, _approval_text(row), buttons=_approval_buttons(reply_id),
    )
    db.set_approval_msg_id(conn, reply_id, msg.id)


async def _send_approved_reply(reply_id: int, conn, user_client) -> None:
    row = db.get_pending_reply(conn, reply_id)
    if row is None:
        return
    try:
        sent = await user_client.send_message(
            row["chat_id"], row["draft_text"], reply_to=row["source_message_id"],
        )
        db.mark_sent(conn, reply_id, sent.id)
    except Exception as e:
        db.mark_failed(conn, reply_id, str(e))


async def on_button_callback(event, conn, user_client) -> None:
    data = event.data.decode()
    action, _, id_str = data.partition(":")
    reply_id = int(id_str)

    if action == "approve":
        won = db.try_resolve_pending(conn, reply_id, "approved")
        if won:
            await _send_approved_reply(reply_id, conn, user_client)
            row = db.get_pending_reply(conn, reply_id)
            status_line = "Sent." if row["status"] == "sent" else f"Failed: {row['error']}"
            await event.edit(f"{_approval_text(row)}\n\n**{status_line}**", buttons=None)
        else:
            row = db.get_pending_reply(conn, reply_id)
            await event.answer(f"Already {row['status']}.", alert=True)

    elif action == "reject":
        won = db.try_resolve_pending(conn, reply_id, "rejected")
        row = db.get_pending_reply(conn, reply_id)
        if won:
            await event.edit(f"{_approval_text(row)}\n\n**Rejected.**", buttons=None)
        else:
            await event.answer(f"Already {row['status']}.", alert=True)

    elif action == "edit":
        row = db.get_pending_reply(conn, reply_id)
        if row["status"] != "pending":
            await event.answer(f"Already {row['status']}.", alert=True)
            return
        _pending_edits[event.sender_id] = reply_id
        await event.respond("Send the replacement reply text now.")
        await event.answer()


async def on_edit_text_message(event, conn, user_client) -> None:
    """Approval bot's plain-text handler: if the operator is mid-edit, the next message
    they send is the replacement draft text."""
    reply_id = _pending_edits.pop(event.sender_id, None)
    if reply_id is None:
        return
    conn.execute("UPDATE pending_replies SET draft_text = ? WHERE id = ? AND status = 'pending'",
                 (event.raw_text, reply_id))
    conn.commit()
    row = db.get_pending_reply(conn, reply_id)
    await event.respond(f"Updated. Reviewing:\n\n{_approval_text(row)}",
                         buttons=_approval_buttons(reply_id))


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(send_draft_for_approval)
    assert inspect.iscoroutinefunction(on_button_callback)
    assert inspect.iscoroutinefunction(on_edit_text_message)
    print("runner.py (approval half) smoke check OK — signatures present")
