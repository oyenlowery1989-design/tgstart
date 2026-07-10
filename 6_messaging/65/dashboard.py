import os
import sys
import json
import secrets
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict

from fastapi import FastAPI, Request, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import uvicorn

# --- Config & Setup ---
load_dotenv()
if not os.getenv("API_ID") and os.path.exists(".env.local"):
    load_dotenv(".env.local")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DB_PATH = DATA_DIR / "ghost.db"

# --- Auth ---
# Dashboard has write endpoints (toggle config, chat mapping) and reads chat/user data.
# Only skip auth when no DASHBOARD_PASSWORD is set AND we're bound to loopback (see
# startup check below, which refuses to bind non-local without a password).
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
security = HTTPBasic(auto_error=False)

def require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    if not DASHBOARD_PASSWORD:
        return
    valid_user = credentials is not None and secrets.compare_digest(credentials.username, DASHBOARD_USER)
    valid_pass = credentials is not None and secrets.compare_digest(credentials.password, DASHBOARD_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})

app = FastAPI(title="GhostMirror Dashboard", version="2.0.0", dependencies=[Depends(require_auth)])

# Assets
templates = Jinja2Templates(directory="templates")
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Database Helper ---
def get_db_connection():
    if not DB_PATH.exists():
        # Should not happen if runner is started, but safe fallback
        print("DB not found!")
        pass
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    # Hardening per connection
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;") # Good practice
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
    """Bumps the config_meta timestamp to signal Runner to refresh."""
    ts = str(datetime.datetime.now().timestamp())
    execute_query(
        "INSERT OR REPLACE INTO config_meta (key, value) VALUES ('config_bump', ?)", 
        (ts,), 
        commit=True
    )

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Overview Page"""
    # Counts
    monitored = execute_query("SELECT COUNT(*) as c FROM chats WHERE monitored=1", fetchone=True)
    msgs = execute_query("SELECT COUNT(*) as c FROM messages", fetchone=True)
    events = execute_query("SELECT COUNT(*) as c FROM events", fetchone=True)
    
    # Recent Failures
    failures = execute_query("""
        SELECT * FROM events 
        WHERE event_type IN ('mirror_failed_total', 'mirror_fallback_copy') 
        ORDER BY ts DESC LIMIT 5
    """, fetchall=True)
    
    # Recent Events
    recent_events = execute_query("""
        SELECT * FROM events ORDER BY ts DESC LIMIT 10
    """, fetchall=True)
    
    # Version
    # We can try to read schema_version from code or DB if stored, for now arbitrary
    bump = execute_query("SELECT value FROM config_meta WHERE key='config_bump'", fetchone=True)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "monitored_count": monitored['c'] if monitored else 0,
        "message_count": msgs['c'] if msgs else 0,
        "event_count": events['c'] if events else 0,
        "failures": failures,
        "recent_events": recent_events,
        "config_bump": bump['value'] if bump else "0",
        "schema_version": "3" # Phase 3
    })

@app.get("/chats", response_class=HTMLResponse)
async def chats_list(request: Request, page: int = 1):
    """Chats Management"""
    limit = 20
    offset = (page - 1) * limit
    
    total = execute_query("SELECT COUNT(*) as c FROM chats", fetchone=True)['c']
    
    # Left Join with Config to get toggles
    query = """
        SELECT c.*, 
               cfg.toggle_mirror_new, cfg.toggle_log_new, 
               cfg.toggle_edits, cfg.toggle_deletes, cfg.toggle_joins,
               cfg.toggle_admin, cfg.toggle_restrict, cfg.toggle_invites, cfg.toggle_bots, cfg.toggle_bio_worker
        FROM chats c
        LEFT JOIN config cfg ON c.chat_id = cfg.chat_id
        ORDER BY c.title ASC
        LIMIT ? OFFSET ?
    """
    chats = execute_query(query, (limit, offset), fetchall=True)
    
    # Normalize None to default True/1 for display if config row missing (though Runner creates it)
    # Actually runner creates defaults on startup if missing.
    
    total_pages = (total // limit) + 1
    
    return templates.TemplateResponse("chats.html", {
        "request": request,
        "chats": chats,
        "page": page,
        "total_pages": total_pages,
        "total_chats": total
    })

@app.get("/events", response_class=HTMLResponse)
async def events_list(request: Request, page: int = 1, type: str = ""):
    limit = 50
    offset = (page - 1) * limit
    
    params = []
    where_clause = ""
    if type:
        where_clause = "WHERE event_type = ?"
        params.append(type)
        
    count_q = f"SELECT COUNT(*) as c FROM events {where_clause}"
    total = execute_query(count_q, tuple(params), fetchone=True)['c']
    
    params.extend([limit, offset])
    data_q = f"SELECT * FROM events {where_clause} ORDER BY ts DESC LIMIT ? OFFSET ?"
    events = execute_query(data_q, tuple(params), fetchall=True)
    
    total_pages = (total // limit) + 1
    if total_pages == 0: total_pages = 1
    
    return templates.TemplateResponse("events.html", {
        "request": request,
        "events": events,
        "page": page,
        "total_pages": total_pages,
        "total_events": total,
        "type_filter": type
    })

@app.get("/users", response_class=HTMLResponse)
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
    
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users,
        "page": page,
        "total_pages": total_pages,
        "total_users": total,
        "query": q
    })

# --- API Endpoints (Writes) ---

@app.post("/api/toggle/{chat_id}/{key}")
async def api_toggle(chat_id: int, key: str, value: int = Query(...)):
    """
    Flip a toggle key for a chat.
    Valid keys based on config schema:
    toggle_mirror_new, toggle_log_new, 
    toggle_edits, toggle_deletes, toggle_joins,
    toggle_admin, toggle_restrict, toggle_invites, toggle_bots, toggle_bio_worker
    """
    valid_keys = [
        "toggle_mirror_new", "toggle_log_new", 
        "toggle_edits", "toggle_deletes", "toggle_joins",
        "toggle_admin", "toggle_restrict", "toggle_invites", "toggle_bots", "toggle_bio_worker"
    ]
    if key not in valid_keys:
        raise HTTPException(400, "Invalid key")
    
    # Ensure config row exists
    execute_query("INSERT OR IGNORE INTO config (chat_id) VALUES (?)", (chat_id,), commit=True)
    
    # Update
    # Use generic query construction safely since key is whitelisted
    query = f"UPDATE config SET {key} = ? WHERE chat_id = ?"
    execute_query(query, (value, chat_id), commit=True)
    
    # Bump
    bump_config()
    
    return {"status": "ok", "new_value": value}

@app.post("/api/chats/{chat_id}/monitor")
async def api_monitor(chat_id: int, value: int = Query(...)):
    """Toggle monitored status in chats table."""
    execute_query("UPDATE chats SET monitored = ? WHERE chat_id = ?", (value, chat_id), commit=True)
    bump_config()
    return {"status": "ok", "new_value": value}




@app.get("/api/recent_events_v2")
async def api_recent_events_v2(limit: int = 20, after_ts: str = ""):
    if limit > 200: limit = 200
    
    query = "SELECT * FROM events"
    params = []
    
    if after_ts:
        query += " WHERE ts > ?"
        params.append(after_ts)
        
    query += " ORDER BY ts ASC LIMIT ?"
    params.append(limit)
    
    
    events = execute_query(query, tuple(params), fetchall=True)
    return {"events": events}


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, q: str = ""):
    """Setup & Mapping Page"""
    where = ""
    params = []
    if q:
        where = "WHERE title LIKE ? OR chat_id LIKE ?"
        wild = f"%{q}%"
        params = [wild, wild]
    
    # 1. Fetch Sources (All chats matching query)
    # We want monitored first, then alpha
    query = f"SELECT * FROM chats {where} ORDER BY monitored DESC, title ASC"
    chats = execute_query(query, tuple(params), fetchall=True)
    
    # 2. Fetch Eligible Destinations (Channels only? Or Groups too?)
    # For now, let's allow any channel/supergroup/group
    dest_query = "SELECT chat_id, title FROM chats WHERE type IN ('channel', 'supergroup', 'group') ORDER BY title ASC"
    destinations = execute_query(dest_query, fetchall=True)
    
    return templates.TemplateResponse("setup.html", {
        "request": request,
        "chats": chats,
        "destinations": destinations,
        "query": q
    })

@app.post("/api/chat_mapping")
async def api_chat_mapping(payload: dict):
    """
    { "chat_id": 123, "monitored": true, "backup_chat_id": 456 }
    """
    chat_id = payload.get("chat_id")
    monitored = 1 if payload.get("monitored") else 0
    backup_id = payload.get("backup_chat_id") # Can be None/int
    
    if not chat_id:
        raise HTTPException(400, "Missing chat_id")
        
    # Update chats table
    execute_query("""
        UPDATE chats 
        SET monitored = ?, backup_chat_id = ?
        WHERE chat_id = ?
    """, (monitored, backup_id, chat_id), commit=True)
    
    # Ensure config row exists
    # If starting to monitor, we want full config row available for toggles
    execute_query("INSERT OR IGNORE INTO config (chat_id) VALUES (?)", (chat_id,), commit=True)
    
    # Bump
    bump_config()
    return {"status": "ok"}



if __name__ == "__main__":
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", 8000))

    if host not in ("127.0.0.1", "localhost", "::1") and not DASHBOARD_PASSWORD:
        print(f"Refusing to start: DASHBOARD_HOST={host} is non-local but no DASHBOARD_PASSWORD is set.")
        print("Set DASHBOARD_PASSWORD in .env or .env.local, or bind to 127.0.0.1.")
        sys.exit(1)

    if DASHBOARD_PASSWORD:
        print(f"Starting Dashboard on http://{host}:{port} (HTTP Basic auth enabled, user={DASHBOARD_USER})")
    else:
        print(f"Starting Dashboard on http://{host}:{port} (no auth, loopback-only)")
    uvicorn.run(app, host=host, port=port)
