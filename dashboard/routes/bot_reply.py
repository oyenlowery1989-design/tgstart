"""Bot Reply tab: pending-approval queue, per-chat config, and runner settings."""
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from telethon.tl.types import Channel, Chat, User
from telethon.utils import get_peer_id

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BOT_REPLY_DIR = ROOT_DIR / "6_messaging" / "bot_reply"
if str(BOT_REPLY_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_REPLY_DIR))
import db as bot_reply_db  # noqa: E402  (path must be set up first)

from dashboard.state import get_active_session, list_sessions, FRONTEND_AVAILABLE
from dashboard.tg_client import make_client, session_lock
from dashboard.templates_env import render_template as _render_template

router = APIRouter(prefix="/reply")

# Single shared connection, reused across requests (sqlite3 with check_same_thread=False
# is safe to share in this single-process FastAPI app — matches the pattern
# dashboard/routes/ghost_mirror.py uses). A fresh connection per request, as this module
# originally did, leaked a WAL file handle on every page load and toggle.
_conn_singleton = None


def _conn():
    global _conn_singleton
    if _conn_singleton is None:
        _conn_singleton = bot_reply_db.get_connection()
    return _conn_singleton


async def _list_dialogs_marked(session_name: str):
    """Like dashboard.services.chats_service.list_dialogs, but yields Telethon's marked
    chat id (telethon.utils.get_peer_id) instead of the bare entity id. chat_config.chat_id
    and the runner's event.chat_id both live in the marked namespace (-100<channel_id> for
    channels/supergroups, -<chat_id> for basic groups, unchanged for users); chats_service's
    bare id is relied on by the already-working chats/scrape/stats/purge tabs and must not
    change, so this subsystem normalizes locally instead."""
    rows = []
    async with session_lock(session_name):
        client = make_client(session_name)
        await client.start()
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
                    "chat_id": get_peer_id(entity),
                    "name": dialog.name,
                    "type": dialog_type,
                })
        finally:
            await client.disconnect()
    return rows


def _queue_data():
    conn = _conn()
    pending = bot_reply_db.list_pending_replies(conn, status="pending")
    approved = bot_reply_db.list_pending_replies(conn, status="approved")
    recent = [r for r in bot_reply_db.list_pending_replies(conn)
              if r["status"] in ("sent", "rejected", "failed", "expired")][:20]

    session_name = bot_reply_db.get_setting(conn, "session_name")
    bot_token = os.getenv("BOT_REPLY_APPROVAL_BOT_TOKEN", "")
    operator_user_id = os.getenv("BOT_REPLY_OPERATOR_USER_ID", "")
    configured = bool(session_name) and bool(bot_token) and bool(operator_user_id)

    return {"configured": configured, "pending": pending, "approved": approved, "recent": recent}


@router.get("", response_class=HTMLResponse)
async def reply_queue_page(request: Request):
    data = _queue_data()
    return _render_template("reply/index.html", {
        "request": request, **data,
        "active_session": get_active_session(request), "all_sessions": list_sessions(),
        "frontend_available": FRONTEND_AVAILABLE,
    })


@router.get("/api/queue")
async def api_queue():
    return _queue_data()


@router.get("/setup", response_class=HTMLResponse)
async def reply_setup_page(request: Request):
    conn = _conn()
    session_name = bot_reply_db.get_setting(conn, "session_name") or get_active_session(request)
    dialogs = []
    error = None
    if session_name:
        try:
            dialogs = await _list_dialogs_marked(session_name)
        except Exception as e:
            error = str(e)

    configs = {}
    cur = conn.execute("SELECT * FROM chat_config")
    for row in cur.fetchall():
        configs[row["chat_id"]] = dict(row)

    rows = []
    for d in dialogs:
        cfg = configs.get(d["chat_id"], {})
        rows.append({
            "chat_id": d["chat_id"], "name": d["name"], "type": d["type"],
            "enabled": bool(cfg.get("enabled", 0)),
            "trigger_mode": cfg.get("trigger_mode"),
        })

    settings = {
        "session_name": bot_reply_db.get_setting(conn, "session_name", ""),
        "provider": bot_reply_db.get_setting(conn, "provider", "vertex"),
        "model": bot_reply_db.get_setting(conn, "model", ""),
        "trigger_mode": bot_reply_db.get_setting(conn, "trigger_mode", "mentions"),
        "small_group_max_size": bot_reply_db.get_setting(conn, "small_group_max_size", "50"),
        "draft_ttl_hours": bot_reply_db.get_setting(conn, "draft_ttl_hours", "6"),
        "history_depth": bot_reply_db.get_setting(conn, "history_depth", "10"),
    }

    return _render_template("reply/setup.html", {
        "request": request, "rows": rows, "error": error, "settings": settings,
        "all_sessions": list_sessions(),
        "active_session": get_active_session(request),
        "frontend_available": FRONTEND_AVAILABLE,
    })


@router.post("/api/chat/{chat_id}/enable")
async def api_enable_chat(chat_id: int, payload: dict):
    conn = _conn()
    title = payload.get("title", str(chat_id))
    enabled = 1 if payload.get("enabled") else 0
    bot_reply_db.upsert_chat_config(conn, chat_id, title, enabled=enabled)
    return {"status": "ok", "enabled": bool(enabled)}


@router.post("/api/chat/{chat_id}/trigger_mode")
async def api_set_trigger_mode(chat_id: int, payload: dict):
    mode = payload.get("trigger_mode")
    if mode not in (None, "always", "mentions", "off"):
        raise HTTPException(400, "trigger_mode must be one of: null, 'always', 'mentions', 'off'")
    conn = _conn()
    title = payload.get("title", str(chat_id))
    bot_reply_db.upsert_chat_config(conn, chat_id, title, trigger_mode=mode)
    return {"status": "ok", "trigger_mode": mode}


@router.post("/api/settings")
async def api_update_settings(payload: dict):
    conn = _conn()
    allowed_keys = {
        "session_name", "provider", "model", "trigger_mode",
        "small_group_max_size", "draft_ttl_hours", "history_depth",
    }
    for key, value in payload.items():
        if key not in allowed_keys:
            raise HTTPException(400, f"Unknown setting: {key}")
        bot_reply_db.set_setting(conn, key, str(value))
    return {"status": "ok"}


@router.post("/api/pending/{reply_id}/approve")
async def api_approve(reply_id: int):
    conn = _conn()
    row = bot_reply_db.get_pending_reply(conn, reply_id)
    if row is None:
        raise HTTPException(404, "No such pending reply")
    won = bot_reply_db.try_resolve_pending(conn, reply_id, "approved")
    if not won:
        raise HTTPException(409, f"Already {row['status']}")
    return {"status": "approved"}


@router.post("/api/pending/{reply_id}/reject")
async def api_reject(reply_id: int):
    conn = _conn()
    row = bot_reply_db.get_pending_reply(conn, reply_id)
    if row is None:
        raise HTTPException(404, "No such pending reply")
    won = bot_reply_db.try_resolve_pending(conn, reply_id, "rejected")
    if not won:
        raise HTTPException(409, f"Already {row['status']}")
    return {"status": "rejected"}


@router.post("/api/pending/{reply_id}/retry")
async def api_retry(reply_id: int):
    conn = _conn()
    row = bot_reply_db.get_pending_reply(conn, reply_id)
    if row is None:
        raise HTTPException(404, "No such pending reply")
    won = bot_reply_db.retry_failed(conn, reply_id)
    if not won:
        raise HTTPException(409, f"Cannot retry from status {row['status']}")
    return {"status": "approved"}
