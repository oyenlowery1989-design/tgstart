"""Bot Reply tab: pending-approval queue, per-chat config, and runner settings."""
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BOT_REPLY_DIR = ROOT_DIR / "6_messaging" / "bot_reply"
if str(BOT_REPLY_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_REPLY_DIR))
import db as bot_reply_db  # noqa: E402  (path must be set up first)

from dashboard.state import get_active_session, list_sessions
from dashboard.services.chats_service import list_dialogs
from dashboard.templates_env import render_template as _render_template

router = APIRouter(prefix="/reply")


def _conn():
    return bot_reply_db.get_connection()


@router.get("", response_class=HTMLResponse)
async def reply_queue_page(request: Request):
    conn = _conn()
    pending = bot_reply_db.list_pending_replies(conn, status="pending")
    approved = bot_reply_db.list_pending_replies(conn, status="approved")
    recent = [r for r in bot_reply_db.list_pending_replies(conn)
              if r["status"] in ("sent", "rejected", "failed", "expired")][:20]
    return _render_template("reply/index.html", {
        "request": request, "pending": pending, "approved": approved, "recent": recent,
        "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.get("/setup", response_class=HTMLResponse)
async def reply_setup_page(request: Request):
    conn = _conn()
    session_name = bot_reply_db.get_setting(conn, "session_name") or get_active_session(request)
    dialogs = []
    error = None
    if session_name:
        try:
            dialogs = await list_dialogs(session_name)
        except Exception as e:
            error = str(e)

    configs = {}
    cur = conn.execute("SELECT * FROM chat_config")
    for row in cur.fetchall():
        configs[row["chat_id"]] = dict(row)

    rows = []
    for d in dialogs:
        cfg = configs.get(d["id"], {})
        rows.append({
            "chat_id": d["id"], "name": d["name"], "type": d["type"],
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
