"""Ghost Mirror routes, ported unchanged from 6_messaging/65/dashboard.py, prefixed /ghost."""
import datetime
import sqlite3
from pathlib import Path
from typing import Optional
import os

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

DB_PATH = Path(__file__).resolve().parent.parent.parent / "6_messaging" / "65" / "data" / "ghost.db"

# Initialize Jinja2 environment directly to avoid caching issues
_template_dir = str(Path(__file__).resolve().parent.parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)

router = APIRouter(prefix="/ghost")


def _render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def execute_query(query: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False, commit: bool = False):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
            return cur.lastrowid
        if fetchone:
            row = cur.fetchone()
            return dict(row) if row else None
        if fetchall:
            return [dict(row) for row in cur.fetchall()]
        return cur
    finally:
        conn.close()


def bump_config():
    ts = str(datetime.datetime.now().timestamp())
    execute_query("INSERT OR REPLACE INTO config_meta (key, value) VALUES ('config_bump', ?)", (ts,), commit=True)


@router.get("", response_class=HTMLResponse)
async def home(request: Request):
    monitored = execute_query("SELECT COUNT(*) as c FROM chats WHERE monitored=1", fetchone=True)
    msgs = execute_query("SELECT COUNT(*) as c FROM messages", fetchone=True)
    events = execute_query("SELECT COUNT(*) as c FROM events", fetchone=True)
    failures = execute_query("""
        SELECT * FROM events
        WHERE event_type IN ('mirror_failed_total', 'mirror_fallback_copy')
        ORDER BY ts DESC LIMIT 5
    """, fetchall=True)
    recent_events = execute_query("SELECT * FROM events ORDER BY ts DESC LIMIT 10", fetchall=True)
    bump = execute_query("SELECT value FROM config_meta WHERE key='config_bump'", fetchone=True)
    html = _render_template("ghost/index.html", {
        "request": request,
        "monitored_count": monitored['c'] if monitored else 0,
        "message_count": msgs['c'] if msgs else 0,
        "event_count": events['c'] if events else 0,
        "failures": failures,
        "recent_events": recent_events,
        "config_bump": bump['value'] if bump else "0",
        "schema_version": "3",
    })
    return html


@router.get("/chats", response_class=HTMLResponse)
async def chats_list(request: Request, page: int = 1):
    limit = 20
    offset = (page - 1) * limit
    total = execute_query("SELECT COUNT(*) as c FROM chats", fetchone=True)['c']
    query = """
        SELECT c.*,
               cfg.toggle_mirror_new, cfg.toggle_log_new,
               cfg.toggle_edits, cfg.toggle_deletes, cfg.toggle_joins,
               cfg.toggle_admin, cfg.toggle_restrict, cfg.toggle_invites, cfg.toggle_bots, cfg.toggle_bio_worker,
               cfg.toggle_reactions
        FROM chats c
        LEFT JOIN config cfg ON c.chat_id = cfg.chat_id
        ORDER BY c.title ASC
        LIMIT ? OFFSET ?
    """
    chats = execute_query(query, (limit, offset), fetchall=True)
    total_pages = (total // limit) + 1
    html = _render_template("ghost/chats.html", {
        "request": request, "chats": chats, "page": page, "total_pages": total_pages, "total_chats": total,
    })
    return html


@router.get("/events", response_class=HTMLResponse)
async def events_list(request: Request, page: int = 1, type: str = ""):
    limit = 50
    offset = (page - 1) * limit
    params = []
    where_clause = ""
    if type:
        where_clause = "WHERE event_type = ?"
        params.append(type)
    total = execute_query(f"SELECT COUNT(*) as c FROM events {where_clause}", tuple(params), fetchone=True)['c']
    params.extend([limit, offset])
    events = execute_query(f"SELECT * FROM events {where_clause} ORDER BY ts DESC LIMIT ? OFFSET ?", tuple(params), fetchall=True)
    total_pages = max((total // limit) + 1, 1)
    html = _render_template("ghost/events.html", {
        "request": request, "events": events, "page": page, "total_pages": total_pages,
        "total_events": total, "type_filter": type,
    })
    return html


@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request, page: int = 1, q: str = ""):
    limit = 50
    offset = (page - 1) * limit
    where = ""
    params = []
    if q:
        where = "WHERE username LIKE ? OR first_name LIKE ? OR user_id = ?"
        wild = f"%{q}%"
        params = [wild, wild, q if q.isdigit() else -1]
    total = execute_query(f"SELECT COUNT(*) as c FROM users {where}", tuple(params), fetchone=True)['c']
    params.extend([limit, offset])
    users = execute_query(f"SELECT * FROM users {where} ORDER BY last_seen DESC LIMIT ? OFFSET ?", tuple(params), fetchall=True)
    total_pages = (total // limit) + 1
    html = _render_template("ghost/users.html", {
        "request": request, "users": users, "page": page, "total_pages": total_pages,
        "total_users": total, "query": q,
    })
    return html


@router.post("/api/toggle/{chat_id}/{key}")
async def api_toggle(chat_id: int, key: str, value: int = Query(...)):
    valid_keys = [
        "toggle_mirror_new", "toggle_log_new", "toggle_edits", "toggle_deletes", "toggle_joins",
        "toggle_admin", "toggle_restrict", "toggle_invites", "toggle_bots", "toggle_bio_worker",
        "toggle_reactions",
    ]
    if key not in valid_keys:
        raise HTTPException(400, "Invalid key")
    execute_query("INSERT OR IGNORE INTO config (chat_id) VALUES (?)", (chat_id,), commit=True)
    execute_query(f"UPDATE config SET {key} = ? WHERE chat_id = ?", (value, chat_id), commit=True)
    bump_config()
    return {"status": "ok", "new_value": value}


@router.post("/api/chats/{chat_id}/monitor")
async def api_monitor(chat_id: int, value: int = Query(...)):
    execute_query("UPDATE chats SET monitored = ? WHERE chat_id = ?", (value, chat_id), commit=True)
    bump_config()
    return {"status": "ok", "new_value": value}


@router.get("/api/recent_events_v2")
async def api_recent_events_v2(limit: int = 20, after_ts: str = ""):
    if limit > 200:
        limit = 200
    query = "SELECT * FROM events"
    params = []
    if after_ts:
        query += " WHERE ts > ?"
        params.append(after_ts)
    query += " ORDER BY ts ASC LIMIT ?"
    params.append(limit)
    events = execute_query(query, tuple(params), fetchall=True)
    return {"events": events}


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, q: str = ""):
    where = ""
    params = []
    if q:
        where = "WHERE title LIKE ? OR chat_id LIKE ?"
        wild = f"%{q}%"
        params = [wild, wild]
    query = f"SELECT * FROM chats {where} ORDER BY monitored DESC, title ASC"
    chats = execute_query(query, tuple(params), fetchall=True)
    dest_query = "SELECT chat_id, title FROM chats WHERE type IN ('channel', 'supergroup', 'group') ORDER BY title ASC"
    destinations = execute_query(dest_query, fetchall=True)
    html = _render_template("ghost/setup.html", {
        "request": request, "chats": chats, "destinations": destinations, "query": q,
    })
    return html


@router.post("/api/chat_mapping")
async def api_chat_mapping(payload: dict):
    chat_id = payload.get("chat_id")
    monitored = 1 if payload.get("monitored") else 0
    backup_id = payload.get("backup_chat_id")
    if not chat_id:
        raise HTTPException(400, "Missing chat_id")
    execute_query("UPDATE chats SET monitored = ?, backup_chat_id = ? WHERE chat_id = ?", (monitored, backup_id, chat_id), commit=True)
    execute_query("INSERT OR IGNORE INTO config (chat_id) VALUES (?)", (chat_id,), commit=True)
    bump_config()
    return {"status": "ok"}
