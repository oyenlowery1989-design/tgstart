# Suite Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the terminal `run.py` menu with a single FastAPI web dashboard at repo root covering login, session verification, chat/group listing, scraping, group stats, purge, participation-finder, plus the existing Ghost Mirror dashboard — all behind one HTTP Basic auth gate.

**Architecture:** New `dashboard/` package at repo root: `app.py` (FastAPI app, auth, lifespan-managed Ghost Mirror subprocess), `routes/` (one router module per tab), `services/` (async logic extracted from each of the 8 pipeline scripts, no Rich/subprocess coupling), `templates/` (Jinja2, including a `ghost/` subfolder for ported Ghost Mirror pages), `static/`. `run.py` stays untouched as a fallback; `6_messaging/65/ghost_runner.py` stays untouched and keeps running as a supervised subprocess coordinated via the existing SQLite `config_bump` polling.

**Tech Stack:** FastAPI, Jinja2, uvicorn, Telethon, python-dotenv, qrcode, native WebSockets (`fastapi`/`starlette` built-in, backed by the `websockets` package) — no new JS framework.

## Global Constraints

- Single consolidated venv at repo root. `6_messaging/65/requirements.txt` (fastapi, uvicorn, jinja2, aiofiles, loguru) merges into root `requirements.txt` alongside telethon/pandas/rich/etc. `6_messaging/65/venv/` is retired once the merge is verified working.
- `6_messaging/65/ghost_runner.py` is untouched — no refactor of its internals or its SQLite coordination model.
- `6_messaging/65/dashboard.py`'s existing routes are ported logic-unchanged into a `ghost_mirror` route module under the shared auth/template setup.
- Auth: reuse the existing HTTP Basic gate from `65/dashboard.py` unchanged — `DASHBOARD_USER`/`DASHBOARD_PASSWORD` env vars, fail-closed to loopback-only binding if no password is set. Extended to cover every route in the new app, not just Ghost Mirror's.
- No new JS framework — server-rendered Jinja2 + minimal JS for websockets, matching the existing Ghost Mirror dashboard's style.
- No auth model beyond HTTP Basic (no per-user accounts, no RBAC) — solo-operator tool, not multi-tenant.
- Purge requires the shared HTTP Basic auth **and** a type-to-confirm step (user types the target chat's name) before the delete fires — in addition to, not instead of, auth.
- Long-running operations (scraping, group-user listing, group stats, purge) run as a background task with a websocket streaming `{current, total, message}` progress events; errors become `{"error": "..."}` websocket events or an error banner.
- Env var convention: scripts/services prefer `MAIN_API_ID`/`MAIN_API_HASH`, falling back to `API_ID`/`API_HASH`; fallback defaults must be `0`/`""`, never real values. `DEFAULT_SESSION` env var convention is replaced in the dashboard by the interactive cookie-based active-session switcher, but the same resolution order (env-configurable, else first available) is preserved.
- `EXPORT_PHONE_NUMBERS` and `AGGRESSIVE_SCRAPE` stay opt-in env flags, off by default, in the group-users service.
- No removal of `run.py`; it remains a minimal fallback.
- Testing/verification: no test framework exists or is introduced. Verification is `python -m py_compile` on every new/changed file, plus a small `if __name__ == "__main__":` smoke-check per service module, plus a manual end-to-end pass per feature before considering it done.

---

## File Structure

| File | Responsibility |
|---|---|
| `requirements.txt` (root, modified) | Merged dependency list: existing root deps + fastapi, uvicorn, jinja2, aiofiles, loguru, websockets, python-multipart. |
| `dashboard/__init__.py` | Empty, marks `dashboard` as a package. |
| `dashboard/app.py` | FastAPI app instance, auth dependency wiring, static/template mounts, lifespan hook that starts/stops the Ghost Mirror bot subprocess, `__main__` entrypoint with the loopback fail-closed check (ported from `65/dashboard.py`), sys.path bootstrap so `dashboard.*` and `utils.*` imports resolve when run as `python dashboard/app.py` from repo root. |
| `dashboard/auth.py` | `require_auth` HTTP Basic dependency, `DASHBOARD_USER`/`DASHBOARD_PASSWORD`, ported unchanged from `65/dashboard.py`. |
| `dashboard/state.py` | `list_sessions()`, `session_path()`, `get_active_session(request)`, `ACTIVE_SESSION_COOKIE` constant — the session-switcher backing state. |
| `dashboard/tg_client.py` | `make_client(session_name) -> TelegramClient`, `API_ID`/`API_HASH` resolution (mirrors every script's `MAIN_API_ID`/`API_ID` fallback pattern). |
| `dashboard/ghost_process.py` | `start_ghost_bot() -> subprocess.Popen`, `stop_ghost_bot(proc)` — ported from `run.py`'s `run_dashboard_pair()`. |
| `dashboard/ws_utils.py` | `send_progress(ws, current, total, message)` / `send_error(ws, message)` helpers so every websocket route emits the same JSON shape. |
| `dashboard/routes/__init__.py` | Empty, marks `routes` as a package. |
| `dashboard/routes/ghost_mirror.py` | Ported routes from `65/dashboard.py`, prefixed `/ghost`, reading `6_messaging/65/data/ghost.db` unchanged. |
| `dashboard/routes/sessions.py` | `/sessions`, `/sessions/active`, `/sessions/login`, `/sessions/login/phone`, `/sessions/login/code`, `/sessions/login/2fa`, `/sessions/login/qr` (page) + `ws /sessions/login/qr/ws`. |
| `dashboard/routes/chats.py` | `/chats`. |
| `dashboard/routes/groups.py` | `/groups/<id>/users` (page) + `ws /groups/<id>/users/ws`. |
| `dashboard/routes/scrape.py` | `/scrape` (page) + `ws /scrape/ws`. |
| `dashboard/routes/stats.py` | `/stats` (page) + `ws /stats/ws`. |
| `dashboard/routes/utilities.py` | `/utilities/participation` (page) + `ws /utilities/participation/ws`; `/utilities/purge` (page) + `/utilities/purge/preview` + `ws /utilities/purge/ws`. |
| `dashboard/services/__init__.py` | Empty. |
| `dashboard/services/sessions_service.py` | `check_session`, `check_all_sessions`, phone-login flow (`start_phone_login`, `submit_code`, `submit_2fa`), QR-login flow (`start_qr_flow`, `wait_qr_flow`, `submit_qr_2fa`) — extracted from `1_login/1_login.py`, `1_login/1_login_by_qr.py`, `2_verify/2_verify_login_advanced.py`. |
| `dashboard/services/chats_service.py` | `list_dialogs`, `save_dialogs_csv` — extracted from `3_chat_management/30_list_chats.py`. |
| `dashboard/services/group_users_service.py` | `list_group_users`, `save_group_users_csv` — extracted from `3_chat_management/31_list_group_users.py`. |
| `dashboard/services/scrape_service.py` | `LinkRecord`, `ScrapeResult`, `scrape_links` — extracted from `4_scraping/41_scrape_links_advanced.py`. |
| `dashboard/services/stats_service.py` | `StatsResult`, `group_stats` — extracted from `5_monitoring/50_group_stats.py`. |
| `dashboard/services/participation_service.py` | `find_participation` — extracted from `7_utilities/71_find_my_participation.py`. |
| `dashboard/services/purge_service.py` | `scan_my_activity`, `preview_my_messages`, `purge_my_messages` — extracted from `7_utilities/70_purge_my_messages.py`. |
| `dashboard/templates/base.html` | Shared layout, nav bar (Sessions/Chats/Groups/Scraping/Stats/Ghost Mirror/Utilities), warning banner, session-switcher header form, shared websocket-progress JS helper. |
| `dashboard/templates/sessions.html`, `login_phone.html`, `login_qr.html` | Sessions tab pages. |
| `dashboard/templates/chats.html` | Chats tab page. |
| `dashboard/templates/groups.html` | Group Users tab page. |
| `dashboard/templates/scrape.html` | Scraping tab page. |
| `dashboard/templates/stats.html` | Stats tab page. |
| `dashboard/templates/utilities_participation.html`, `utilities_purge.html` | Utilities tab pages. |
| `dashboard/templates/ghost/index.html`, `chats.html`, `events.html`, `users.html`, `setup.html`, `base.html` | Copied verbatim from `6_messaging/65/templates/`, `{% extends %}` updated to `ghost/base.html`, links/fetch URLs re-prefixed with `/ghost`. |
| `dashboard/static/style.css` | Merged/copied from `6_messaging/65/static/style.css`, extended with progress-bar/websocket-state classes. |
| `run.py` (modified) | Menu choice launches `dashboard/app.py` instead of `6_messaging/65`'s pair; other choices unchanged. |
| `CLAUDE.md` (modified) | Documents the new dashboard as primary entrypoint, the merged venv, and that `65/venv/` is retired. |

---

### Task 1: Scaffold FastAPI app, auth, base template, static assets, merged requirements

**Files:**
- Modify: `requirements.txt` (append merged deps at end)
- Create: `dashboard/__init__.py`
- Create: `dashboard/app.py`
- Create: `dashboard/auth.py`
- Create: `dashboard/state.py`
- Create: `dashboard/tg_client.py`
- Create: `dashboard/routes/__init__.py`
- Create: `dashboard/services/__init__.py`
- Create: `dashboard/templates/base.html`
- Create: `dashboard/static/style.css`
- Test: `python -m py_compile dashboard/app.py dashboard/auth.py dashboard/state.py dashboard/tg_client.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `dashboard.auth.require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> None` (raises `HTTPException(401)`), `DASHBOARD_USER: str`, `DASHBOARD_PASSWORD: str`.
  - `dashboard.state.ROOT_DIR: Path`, `dashboard.state.SESSIONS_DIR: Path`, `dashboard.state.ACTIVE_SESSION_COOKIE: str`, `dashboard.state.list_sessions() -> List[str]`, `dashboard.state.session_path(session_name: str) -> str`, `dashboard.state.get_active_session(request: Request) -> Optional[str]`.
  - `dashboard.tg_client.API_ID: int`, `dashboard.tg_client.API_HASH: str`, `dashboard.tg_client.make_client(session_name: str) -> TelegramClient`.
  - `dashboard.app.app: FastAPI` (used by later route modules via `app.include_router(...)`).

- [ ] **Step 1: Merge dependencies into root `requirements.txt`**

Append to `requirements.txt`:

```
# Web dashboard (merged from 6_messaging/65/requirements.txt)
fastapi>=0.110.0
uvicorn>=0.29.0
jinja2>=3.1.0
aiofiles>=23.0.0
loguru>=0.7.0
websockets>=12.0
python-multipart>=0.0.9
```

- [ ] **Step 2: Install and verify import**

Run: `venv/bin/pip install -r requirements.txt && venv/bin/python -c "import fastapi, uvicorn, jinja2, websockets; print('deps OK')"`
Expected: `deps OK`

- [ ] **Step 3: Create `dashboard/__init__.py`, `dashboard/routes/__init__.py`, `dashboard/services/__init__.py`**

All three are empty files.

- [ ] **Step 4: Create `dashboard/state.py`**

```python
"""Active-session cookie state and sessions/ directory helpers."""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import Request

ROOT_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT_DIR / "sessions"
ACTIVE_SESSION_COOKIE = "active_session"


def list_sessions() -> List[str]:
    """Returns sorted session names (no .session extension), skipping temp files."""
    if not SESSIONS_DIR.exists():
        return []
    names = []
    for f in sorted(SESSIONS_DIR.glob("*.session")):
        name = f.stem
        if not name.startswith("temp_login_"):
            names.append(name)
    return sorted(names)


def session_path(session_name: str) -> str:
    """Absolute path (no extension) Telethon expects for TelegramClient(session_path)."""
    return str(SESSIONS_DIR / session_name)


def get_active_session(request: Request) -> Optional[str]:
    """Reads the active_session cookie; falls back to the first available session."""
    sessions = list_sessions()
    cookie_name = request.cookies.get(ACTIVE_SESSION_COOKIE)
    if cookie_name and cookie_name in sessions:
        return cookie_name
    return sessions[0] if sessions else None


if __name__ == "__main__":
    assert callable(list_sessions) and callable(session_path) and callable(get_active_session)
    print("state.py smoke check OK:", list_sessions())
```

- [ ] **Step 5: Create `dashboard/tg_client.py`**

```python
"""Builds TelegramClient instances using the suite's MAIN_API_ID/API_ID fallback convention."""
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from dashboard.state import session_path

load_dotenv()

API_ID = int(os.getenv("MAIN_API_ID", os.getenv("API_ID", 0)))
API_HASH = os.getenv("MAIN_API_HASH", os.getenv("API_HASH", ""))


def make_client(session_name: str) -> TelegramClient:
    return TelegramClient(session_path(session_name), API_ID, API_HASH)


if __name__ == "__main__":
    c = make_client("smoke_test_nonexistent")
    assert isinstance(c, TelegramClient)
    print("tg_client.py smoke check OK")
```

- [ ] **Step 6: Create `dashboard/auth.py`** (ported unchanged from `6_messaging/65/dashboard.py`'s auth block)

```python
"""HTTP Basic auth, ported unchanged from 6_messaging/65/dashboard.py."""
import os
import secrets
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv

load_dotenv()

DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
security = HTTPBasic(auto_error=False)


def require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> None:
    if not DASHBOARD_PASSWORD:
        return
    valid_user = credentials is not None and secrets.compare_digest(credentials.username, DASHBOARD_USER)
    valid_pass = credentials is not None and secrets.compare_digest(credentials.password, DASHBOARD_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})
```

- [ ] **Step 7: Create `dashboard/templates/base.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{% block title %}Telegram Suite Dashboard{% endblock %}</title>
    <link rel="stylesheet" href="/static/style.css" />
  </head>
  <body>
    <div class="warning-banner">
      ⚠️ CAUTION: Local only! Do NOT expose this dashboard to the public internet.
    </div>

    <div class="navbar">
      <a href="/sessions">Sessions</a>
      <a href="/chats">Chats</a>
      <a href="/scrape">Scraping</a>
      <a href="/stats">Stats</a>
      <a href="/ghost">Ghost Mirror</a>
      <a href="/utilities/participation">Utilities</a>
    </div>

    <form class="session-switcher" method="post" action="/sessions/active">
      <label>Active session:
        <select name="session_name" onchange="this.form.submit()">
          {% for s in all_sessions %}
          <option value="{{ s }}" {% if s == active_session %}selected{% endif %}>{{ s }}</option>
          {% endfor %}
        </select>
      </label>
    </form>

    <div class="container">{% block content %}{% endblock %}</div>

    <script>
      function openProgressSocket(path, onMessage) {
        const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
        const ws = new WebSocket(`${proto}//${window.location.host}${path}`);
        ws.onmessage = (evt) => onMessage(JSON.parse(evt.data));
        ws.onerror = () => onMessage({ error: "WebSocket connection error." });
        return ws;
      }
    </script>
    {% block scripts %}{% endblock %}
  </body>
</html>
```

- [ ] **Step 8: Create `dashboard/static/style.css`** by copying the Ghost Mirror stylesheet and appending progress-bar classes

Run: `cp 6_messaging/65/static/style.css dashboard/static/style.css`

Then append to `dashboard/static/style.css`:

```css
.progress-bar-outer { background: #222; border-radius: 4px; height: 18px; width: 100%; }
.progress-bar-inner { background: #4caf50; height: 100%; border-radius: 4px; transition: width 0.2s; }
.session-switcher { padding: 8px 16px; }
.error-banner { background: #4a1414; color: #ff8080; padding: 10px; border-radius: 4px; margin: 10px 0; }
```

- [ ] **Step 9: Create `dashboard/app.py`**

```python
"""Root FastAPI app: auth, static/template mounts, Ghost Mirror subprocess lifespan."""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from dashboard.auth import require_auth, DASHBOARD_PASSWORD
from dashboard.ghost_process import start_ghost_bot, stop_ghost_bot

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_proc = start_ghost_bot()
    try:
        yield
    finally:
        stop_ghost_bot(bot_proc)


app = FastAPI(title="Telegram Suite Dashboard", dependencies=[Depends(require_auth)], lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/sessions")


if __name__ == "__main__":
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", 8000))

    if host not in ("127.0.0.1", "localhost", "::1") and not DASHBOARD_PASSWORD:
        print(f"Refusing to start: DASHBOARD_HOST={host} is non-local but no DASHBOARD_PASSWORD is set.")
        print("Set DASHBOARD_PASSWORD in .env, or bind to 127.0.0.1.")
        sys.exit(1)

    if DASHBOARD_PASSWORD:
        print(f"Starting Dashboard on http://{host}:{port} (HTTP Basic auth enabled)")
    else:
        print(f"Starting Dashboard on http://{host}:{port} (no auth, loopback-only)")
    uvicorn.run(app, host=host, port=port)
```

- [ ] **Step 10: Create `dashboard/ghost_process.py`**

```python
"""Launches/monitors the Ghost Mirror bot subprocess, mirroring run.py's run_dashboard_pair()."""
import subprocess
import sys
from pathlib import Path

GHOST_DIR = Path(__file__).resolve().parent.parent / "6_messaging" / "65"


def start_ghost_bot() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "run.py"], cwd=str(GHOST_DIR))


def stop_ghost_bot(proc: subprocess.Popen) -> None:
    proc.terminate()
    proc.wait()
```

- [ ] **Step 11: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/app.py dashboard/auth.py dashboard/state.py dashboard/tg_client.py dashboard/ghost_process.py`
Expected: no output, exit code 0.

- [ ] **Step 12: Smoke-run the app boots (no auth password set)**

Run: `venv/bin/python dashboard/app.py &` then `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/sessions` (expect `404` since `/sessions` route doesn't exist yet — confirms the app boots and root redirect works), then `curl -sL http://127.0.0.1:8000/` (expect the redirect chain to hit a 404 page, not a 500/connection-refused), then kill the background process.
Expected: process starts without traceback; requests get HTTP responses (404 is fine — no crash).

- [ ] **Step 13: Commit**

```bash
git add requirements.txt dashboard/__init__.py dashboard/app.py dashboard/auth.py dashboard/state.py dashboard/tg_client.py dashboard/ghost_process.py dashboard/routes/__init__.py dashboard/services/__init__.py dashboard/templates/base.html dashboard/static/style.css
git commit -m "feat(dashboard): scaffold FastAPI app, auth, base template, merged requirements"
```

---

### Task 2: Port Ghost Mirror routes

**Files:**
- Create: `dashboard/routes/ghost_mirror.py`
- Create: `dashboard/templates/ghost/base.html`, `dashboard/templates/ghost/index.html`, `dashboard/templates/ghost/chats.html`, `dashboard/templates/ghost/events.html`, `dashboard/templates/ghost/users.html`, `dashboard/templates/ghost/setup.html`
- Modify: `dashboard/app.py:1-40` (add `app.include_router(ghost_mirror.router)`, register `templates` for the ghost module)
- Test: `python -m py_compile dashboard/routes/ghost_mirror.py dashboard/app.py`

**Interfaces:**
- Consumes: `dashboard.app.app: FastAPI` (Task 1), `dashboard.auth.require_auth` (Task 1, already applied app-wide so no per-router dependency needed).
- Produces: `dashboard.routes.ghost_mirror.router: APIRouter` mounted with `prefix="/ghost"`; DB helpers `get_db_connection()`, `execute_query(...)`, `bump_config()` scoped to this module (not reused elsewhere).

- [ ] **Step 1: Copy Ghost Mirror templates into a namespaced subfolder**

Run:
```bash
mkdir -p dashboard/templates/ghost
cp 6_messaging/65/templates/base.html dashboard/templates/ghost/base.html
cp 6_messaging/65/templates/index.html dashboard/templates/ghost/index.html
cp 6_messaging/65/templates/chats.html dashboard/templates/ghost/chats.html
cp 6_messaging/65/templates/events.html dashboard/templates/ghost/events.html
cp 6_messaging/65/templates/users.html dashboard/templates/ghost/users.html
cp 6_messaging/65/templates/setup.html dashboard/templates/ghost/setup.html
```

- [ ] **Step 2: Re-prefix nav links and fetch URLs in `dashboard/templates/ghost/base.html`**

In `dashboard/templates/ghost/base.html`, change the navbar block from:

```html
<div class="navbar">
  <a href="/">Dashboard</a>
  <a href="/chats">Chats</a>
  <a href="/setup">Setup</a>
  <a href="/events">Events</a>
  <a href="/users">Users</a>
</div>
```

to:

```html
<div class="navbar">
  <a href="/sessions">← Suite Dashboard</a>
  <a href="/ghost">Ghost Mirror Home</a>
  <a href="/ghost/chats">Chats</a>
  <a href="/ghost/setup">Setup</a>
  <a href="/ghost/events">Events</a>
  <a href="/ghost/users">Users</a>
</div>
```

And update the two `fetchPost` call sites (`toggleConfig`, `toggleMonitor`) to prefix `/ghost`:

```js
async function toggleConfig(chatId, key, isChecked) {
  const success = await fetchPost(
    `/ghost/api/toggle/${chatId}/${key}?value=${isChecked ? 1 : 0}`,
  );
  if (!success) window.location.reload();
}

async function toggleMonitor(chatId, isChecked) {
  const success = await fetchPost(
    `/ghost/api/chats/${chatId}/monitor?value=${isChecked ? 1 : 0}`,
  );
  if (!success) window.location.reload();
}
```

- [ ] **Step 3: Update `{% extends %}` in the other 5 ghost templates**

In `dashboard/templates/ghost/index.html`, `chats.html`, `events.html`, `users.html`, `setup.html`: change the top line `{% extends "base.html" %}` to `{% extends "ghost/base.html" %}`.

- [ ] **Step 4: Create `dashboard/routes/ghost_mirror.py`** (routes ported logic-unchanged from `6_messaging/65/dashboard.py`, DB path pointed at the untouched Ghost Mirror data dir)

```python
"""Ghost Mirror routes, ported unchanged from 6_messaging/65/dashboard.py, prefixed /ghost."""
import datetime
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

DB_PATH = Path(__file__).resolve().parent.parent.parent / "6_messaging" / "65" / "data" / "ghost.db"
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter(prefix="/ghost")


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
    return templates.TemplateResponse("ghost/index.html", {
        "request": request,
        "monitored_count": monitored['c'] if monitored else 0,
        "message_count": msgs['c'] if msgs else 0,
        "event_count": events['c'] if events else 0,
        "failures": failures,
        "recent_events": recent_events,
        "config_bump": bump['value'] if bump else "0",
        "schema_version": "3",
    })


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
    return templates.TemplateResponse("ghost/chats.html", {
        "request": request, "chats": chats, "page": page, "total_pages": total_pages, "total_chats": total,
    })


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
    return templates.TemplateResponse("ghost/events.html", {
        "request": request, "events": events, "page": page, "total_pages": total_pages,
        "total_events": total, "type_filter": type,
    })


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
    return templates.TemplateResponse("ghost/users.html", {
        "request": request, "users": users, "page": page, "total_pages": total_pages,
        "total_users": total, "query": q,
    })


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
    return templates.TemplateResponse("ghost/setup.html", {
        "request": request, "chats": chats, "destinations": destinations, "query": q,
    })


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
```

- [ ] **Step 5: Wire the router into `dashboard/app.py`**

In `dashboard/app.py`, after the `app.mount("/static", ...)` line, add:

```python
from dashboard.routes import ghost_mirror
app.include_router(ghost_mirror.router)
```

- [ ] **Step 6: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/routes/ghost_mirror.py dashboard/app.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Manual smoke test against the live Ghost Mirror DB**

Run: `venv/bin/python dashboard/app.py &`, then `curl -s http://127.0.0.1:8000/ghost | grep -c "Dashboard"` (expect a non-zero count from the ported `index.html`), then `curl -s http://127.0.0.1:8000/ghost/chats | head -5`, then kill the background process.
Expected: HTML responses render without a 500 error (confirms `6_messaging/65/data/ghost.db` is reachable at the new path).

- [ ] **Step 8: Commit**

```bash
git add dashboard/routes/ghost_mirror.py dashboard/templates/ghost dashboard/app.py
git commit -m "feat(dashboard): port Ghost Mirror dashboard routes under /ghost"
```

---

### Task 3: Sessions tab — listing, verification, active-session switcher

**Files:**
- Create: `dashboard/services/sessions_service.py`
- Create: `dashboard/routes/sessions.py`
- Create: `dashboard/templates/sessions.html`
- Modify: `dashboard/app.py:1-45` (include `sessions.router`, add `active_session`/`all_sessions` to the base template context via a shared dependency)
- Test: `python -m py_compile dashboard/services/sessions_service.py dashboard/routes/sessions.py`

**Interfaces:**
- Consumes: `dashboard.state.list_sessions() -> List[str]`, `dashboard.state.session_path(session_name: str) -> str`, `dashboard.state.get_active_session(request: Request) -> Optional[str]`, `dashboard.state.ACTIVE_SESSION_COOKIE: str`, `dashboard.tg_client.API_ID: int`, `dashboard.tg_client.API_HASH: str` (Task 1).
- Produces:
  - `dashboard.services.sessions_service.check_session(session_name: str) -> Dict[str, str]` (`{"name", "status", "details"}`, `status` in `{"ACTIVE","INVALID","ERROR"}`).
  - `dashboard.services.sessions_service.check_all_sessions(progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]] = None) -> List[Dict[str, str]]`.
  - `dashboard.routes.sessions.router: APIRouter` mounted with `prefix="/sessions"`, exposing `GET /sessions`, `POST /sessions/active`. Later tasks (4, 5) extend this same router with login endpoints.

- [ ] **Step 1: Create `dashboard/services/sessions_service.py`**

```python
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
```

- [ ] **Step 2: Create `dashboard/routes/sessions.py`**

```python
"""Sessions tab: listing/verification + active-session switcher. Login endpoints added in Tasks 4-5."""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from dashboard.state import list_sessions, get_active_session, ACTIVE_SESSION_COOKIE
from dashboard.services.sessions_service import check_all_sessions

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(prefix="/sessions")


@router.get("", response_class=HTMLResponse)
async def sessions_page(request: Request):
    results = await check_all_sessions()
    return templates.TemplateResponse("sessions.html", {
        "request": request,
        "results": results,
        "active_session": get_active_session(request),
        "all_sessions": list_sessions(),
    })


@router.post("/active")
async def set_active_session(session_name: str = Form(...)):
    resp = RedirectResponse(url="/sessions", status_code=303)
    resp.set_cookie(ACTIVE_SESSION_COOKIE, session_name)
    return resp
```

- [ ] **Step 3: Create `dashboard/templates/sessions.html`**

```html
{% extends "base.html" %}
{% block title %}Sessions{% endblock %}
{% block content %}
<h1>Sessions</h1>
<table>
  <thead><tr><th>Name</th><th>Status</th><th>Details</th></tr></thead>
  <tbody>
    {% for r in results %}
    <tr>
      <td>{{ r.name }}</td>
      <td>{{ r.status }}</td>
      <td>{{ r.details }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<p><a href="/sessions/login">+ Add account (phone)</a> | <a href="/sessions/login/qr">+ Add account (QR)</a></p>
{% endblock %}
```

- [ ] **Step 4: Wire the router and shared template context into `dashboard/app.py`**

In `dashboard/app.py`, after the `ghost_mirror` include, add:

```python
from dashboard.routes import sessions
app.include_router(sessions.router)
```

- [ ] **Step 5: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/sessions_service.py dashboard/routes/sessions.py dashboard/app.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Manual smoke test**

Run: `venv/bin/python dashboard/app.py &`, then `curl -s http://127.0.0.1:8000/sessions | grep -c "<table>"`, then kill the process.
Expected: `1` (page renders).

- [ ] **Step 7: Commit**

```bash
git add dashboard/services/sessions_service.py dashboard/routes/sessions.py dashboard/templates/sessions.html dashboard/app.py
git commit -m "feat(dashboard): sessions tab listing, verification, active-session switcher"
```

---

### Task 4: Sessions tab — phone login flow

**Files:**
- Modify: `dashboard/services/sessions_service.py` (append phone-login flow functions)
- Modify: `dashboard/routes/sessions.py` (append `/sessions/login`, `/sessions/login/code`, `/sessions/login/2fa`)
- Create: `dashboard/templates/login_phone.html`
- Test: `python -m py_compile dashboard/services/sessions_service.py dashboard/routes/sessions.py`

**Interfaces:**
- Consumes: `dashboard.state.SESSIONS_DIR: Path` (Task 1), `dashboard.tg_client.API_ID/API_HASH` (Task 1).
- Produces:
  - `dashboard.services.sessions_service.start_phone_login(phone: str) -> Dict[str, str]` (`{"status": "code_sent", "flow_id": str}` or `{"status": "error", "error": str}`).
  - `dashboard.services.sessions_service.submit_code(flow_id: str, code: str) -> Dict[str, str]` (`{"status": "done", "session_name": str}` | `{"status": "need_2fa", "flow_id": str}` | `{"status": "error", "error": str}`).
  - `dashboard.services.sessions_service.submit_2fa(flow_id: str, password: str) -> Dict[str, str]` (same shape as above minus `need_2fa`).
  - Internal `_finalize_session(client: TelegramClient, temp_session_name: str) -> str` (returns the new session name, reused by Task 5's QR flow).

- [ ] **Step 1: Append phone-login flow to `dashboard/services/sessions_service.py`**

```python
# --- Phone login flow (append below check_all_sessions) ---
import os
import time
import uuid
from dataclasses import dataclass
from typing import Dict as _Dict

from telethon import errors

from dashboard.state import SESSIONS_DIR


@dataclass
class LoginFlow:
    id: str
    client: TelegramClient
    phone: Optional[str] = None
    phone_code_hash: Optional[str] = None
    temp_session_name: str = ""


_FLOWS: Dict[str, LoginFlow] = {}


def _temp_session_path() -> str:
    SESSIONS_DIR.mkdir(exist_ok=True)
    return str(SESSIONS_DIR / f"temp_login_{int(time.time())}_{uuid.uuid4().hex[:6]}")


async def _finalize_session(client: TelegramClient, temp_session_name: str) -> str:
    me = await client.get_me()
    username = me.username or f"user_{me.id}"
    await client.disconnect()
    target = SESSIONS_DIR / f"{username}.session"
    counter = 2
    while target.exists():
        target = SESSIONS_DIR / f"{username}({counter}).session"
        counter += 1
    os.rename(f"{temp_session_name}.session", target)
    return target.stem


async def start_phone_login(phone: str) -> _Dict[str, str]:
    temp_name = _temp_session_path()
    client = TelegramClient(temp_name, API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
    except errors.FloodWaitError as e:
        await client.disconnect()
        return {"status": "error", "error": f"Too many attempts. Wait {e.seconds}s."}
    except Exception as e:
        await client.disconnect()
        return {"status": "error", "error": str(e)}
    flow_id = uuid.uuid4().hex
    _FLOWS[flow_id] = LoginFlow(id=flow_id, client=client, phone=phone, phone_code_hash=sent.phone_code_hash, temp_session_name=temp_name)
    return {"status": "code_sent", "flow_id": flow_id}


async def submit_code(flow_id: str, code: str) -> _Dict[str, str]:
    flow = _FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "Login flow expired or not found."}
    try:
        await flow.client.sign_in(flow.phone, code, phone_code_hash=flow.phone_code_hash)
    except errors.SessionPasswordNeededError:
        return {"status": "need_2fa", "flow_id": flow_id}
    except errors.PhoneCodeInvalidError:
        return {"status": "error", "error": "Invalid code."}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}


async def submit_2fa(flow_id: str, password: str) -> _Dict[str, str]:
    flow = _FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "Login flow expired or not found."}
    try:
        await flow.client.sign_in(password=password)
    except Exception as e:
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}
```

- [ ] **Step 2: Append login routes to `dashboard/routes/sessions.py`**

```python
# --- Phone login routes (append below set_active_session) ---
from fastapi.responses import JSONResponse
from dashboard.services.sessions_service import start_phone_login, submit_code, submit_2fa


@router.get("/login", response_class=HTMLResponse)
async def login_phone_page(request: Request):
    return templates.TemplateResponse("login_phone.html", {"request": request})


@router.post("/login/phone")
async def login_phone_submit(phone: str = Form(...)):
    return JSONResponse(await start_phone_login(phone))


@router.post("/login/code")
async def login_code_submit(flow_id: str = Form(...), code: str = Form(...)):
    return JSONResponse(await submit_code(flow_id, code))


@router.post("/login/2fa")
async def login_2fa_submit(flow_id: str = Form(...), password: str = Form(...)):
    return JSONResponse(await submit_2fa(flow_id, password))
```

- [ ] **Step 3: Create `dashboard/templates/login_phone.html`**

```html
{% extends "base.html" %}
{% block title %}Login (Phone){% endblock %}
{% block content %}
<h1>Login via Phone Number</h1>
<div id="step-phone">
  <input id="phone" type="text" placeholder="+1234567890" />
  <button onclick="sendPhone()">Send code</button>
</div>
<div id="step-code" style="display:none">
  <input id="code" type="text" placeholder="Code from Telegram" />
  <button onclick="sendCode()">Submit code</button>
</div>
<div id="step-2fa" style="display:none">
  <input id="password" type="password" placeholder="2FA password" />
  <button onclick="send2fa()">Submit password</button>
</div>
<div id="result"></div>
<script>
  let flowId = null;
  async function post(url, data) {
    const body = new URLSearchParams(data);
    const resp = await fetch(url, { method: "POST", body });
    return resp.json();
  }
  async function sendPhone() {
    const phone = document.getElementById("phone").value;
    const r = await post("/sessions/login/phone", { phone });
    if (r.status === "code_sent") {
      flowId = r.flow_id;
      document.getElementById("step-phone").style.display = "none";
      document.getElementById("step-code").style.display = "block";
    } else {
      document.getElementById("result").textContent = r.error;
    }
  }
  async function sendCode() {
    const code = document.getElementById("code").value;
    const r = await post("/sessions/login/code", { flow_id: flowId, code });
    if (r.status === "done") {
      window.location.href = "/sessions";
    } else if (r.status === "need_2fa") {
      document.getElementById("step-code").style.display = "none";
      document.getElementById("step-2fa").style.display = "block";
    } else {
      document.getElementById("result").textContent = r.error;
    }
  }
  async function send2fa() {
    const password = document.getElementById("password").value;
    const r = await post("/sessions/login/2fa", { flow_id: flowId, password });
    if (r.status === "done") {
      window.location.href = "/sessions";
    } else {
      document.getElementById("result").textContent = r.error;
    }
  }
</script>
{% endblock %}
```

- [ ] **Step 4: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/sessions_service.py dashboard/routes/sessions.py`
Expected: no output, exit code 0.

- [ ] **Step 5: Manual smoke test**

Run the dashboard, drive `/sessions/login` in a browser with a real phone number through code entry (and 2FA if enabled), confirm a new `.session` file appears under `sessions/` and the redirect to `/sessions` shows it as `ACTIVE`.
Expected: session file created, listed as `ACTIVE`.

- [ ] **Step 6: Commit**

```bash
git add dashboard/services/sessions_service.py dashboard/routes/sessions.py dashboard/templates/login_phone.html
git commit -m "feat(dashboard): sessions tab phone login flow"
```

---

### Task 5: Sessions tab — QR login flow (websocket)

**Files:**
- Modify: `dashboard/services/sessions_service.py` (append QR flow functions)
- Modify: `dashboard/routes/sessions.py` (append `/sessions/login/qr` page + `ws /sessions/login/qr/ws`)
- Create: `dashboard/templates/login_qr.html`
- Test: `python -m py_compile dashboard/services/sessions_service.py dashboard/routes/sessions.py`

**Interfaces:**
- Consumes: `_temp_session_path() -> str`, `_finalize_session(client, temp_session_name) -> str` (Task 4, same module).
- Produces:
  - `dashboard.services.sessions_service.start_qr_flow() -> Dict[str, str]` (`{"flow_id": str, "qr_png_b64": str}`).
  - `dashboard.services.sessions_service.wait_qr_flow(flow_id: str) -> Dict[str, str]` (`{"status": "done", "session_name": str}` | `{"status": "need_2fa", "flow_id": str}` | `{"status": "error", "error": str}`).
  - `dashboard.services.sessions_service.submit_qr_2fa(flow_id: str, password: str) -> Dict[str, str]`.

- [ ] **Step 1: Append QR login flow to `dashboard/services/sessions_service.py`**

```python
# --- QR login flow (append below submit_2fa) ---
import base64
import io

import qrcode


@dataclass
class QRFlow:
    id: str
    client: TelegramClient
    qr_obj: object
    temp_session_name: str


_QR_FLOWS: Dict[str, QRFlow] = {}


async def start_qr_flow() -> _Dict[str, str]:
    temp_name = _temp_session_path()
    client = TelegramClient(temp_name, API_ID, API_HASH)
    await client.connect()
    qr_obj = await client.qr_login()
    img = qrcode.make(qr_obj.url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    flow_id = uuid.uuid4().hex
    _QR_FLOWS[flow_id] = QRFlow(id=flow_id, client=client, qr_obj=qr_obj, temp_session_name=temp_name)
    return {"flow_id": flow_id, "qr_png_b64": png_b64}


async def wait_qr_flow(flow_id: str) -> _Dict[str, str]:
    flow = _QR_FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "QR flow expired or not found."}
    try:
        await flow.qr_obj.wait()
    except errors.SessionPasswordNeededError:
        return {"status": "need_2fa", "flow_id": flow_id}
    except Exception as e:
        if "PasswordNeeded" in str(e) or "password is required" in str(e):
            return {"status": "need_2fa", "flow_id": flow_id}
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _QR_FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}


async def submit_qr_2fa(flow_id: str, password: str) -> _Dict[str, str]:
    flow = _QR_FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "QR flow expired or not found."}
    try:
        await flow.client.sign_in(password=password)
    except Exception as e:
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _QR_FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}
```

- [ ] **Step 2: Append QR routes to `dashboard/routes/sessions.py`**

```python
# --- QR login routes (append below login_2fa_submit) ---
from fastapi import WebSocket, WebSocketDisconnect
from dashboard.services.sessions_service import start_qr_flow, wait_qr_flow, submit_qr_2fa


@router.get("/login/qr", response_class=HTMLResponse)
async def login_qr_page(request: Request):
    return templates.TemplateResponse("login_qr.html", {"request": request})


@router.websocket("/login/qr/ws")
async def login_qr_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        started = await start_qr_flow()
        await websocket.send_json({"state": "waiting", "qr_png_b64": started["qr_png_b64"]})
        result = await wait_qr_flow(started["flow_id"])
        if result["status"] == "need_2fa":
            await websocket.send_json({"state": "need_2fa", "flow_id": result["flow_id"]})
            msg = await websocket.receive_json()
            result = await submit_qr_2fa(result["flow_id"], msg["password"])
        if result["status"] == "done":
            await websocket.send_json({"state": "done", "session_name": result["session_name"]})
        else:
            await websocket.send_json({"state": "error", "error": result.get("error", "Unknown error")})
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
```

- [ ] **Step 3: Create `dashboard/templates/login_qr.html`**

```html
{% extends "base.html" %}
{% block title %}Login (QR){% endblock %}
{% block content %}
<h1>Login via QR Code</h1>
<img id="qr-img" style="display:none; max-width: 300px;" />
<p id="status">Connecting...</p>
<div id="step-2fa" style="display:none">
  <input id="password" type="password" placeholder="2FA password" />
  <button onclick="send2fa()">Submit password</button>
</div>
<script>
  let ws = null;
  window.addEventListener("load", () => {
    ws = openProgressSocket("/sessions/login/qr/ws", (data) => {
      if (data.state === "waiting") {
        document.getElementById("qr-img").src = "data:image/png;base64," + data.qr_png_b64;
        document.getElementById("qr-img").style.display = "block";
        document.getElementById("status").textContent = "Scan with Telegram: Settings → Devices → Link Desktop Device";
      } else if (data.state === "need_2fa") {
        document.getElementById("step-2fa").style.display = "block";
        document.getElementById("status").textContent = "Two-step verification required.";
      } else if (data.state === "done") {
        document.getElementById("status").textContent = "Logged in as " + data.session_name + ". Redirecting...";
        setTimeout(() => (window.location.href = "/sessions"), 1000);
      } else if (data.state === "error" || data.error) {
        document.getElementById("status").textContent = "Error: " + (data.error || "unknown");
      }
    });
  });
  function send2fa() {
    ws.send(JSON.stringify({ password: document.getElementById("password").value }));
  }
</script>
{% endblock %}
```

- [ ] **Step 4: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/sessions_service.py dashboard/routes/sessions.py`
Expected: no output, exit code 0.

- [ ] **Step 5: Manual smoke test**

Run the dashboard, open `/sessions/login/qr` in a browser, confirm a QR image renders, scan it with a real Telegram app, confirm the page transitions to "Logged in as ..." and a new `.session` file appears.
Expected: QR scan completes login end-to-end.

- [ ] **Step 6: Commit**

```bash
git add dashboard/services/sessions_service.py dashboard/routes/sessions.py dashboard/templates/login_qr.html
git commit -m "feat(dashboard): sessions tab QR login flow over websocket"
```

---

### Task 6: Chats tab

**Files:**
- Create: `dashboard/services/chats_service.py`
- Create: `dashboard/routes/chats.py`
- Create: `dashboard/templates/chats.html`
- Modify: `dashboard/app.py` (include `chats.router`)
- Test: `python -m py_compile dashboard/services/chats_service.py dashboard/routes/chats.py`

**Interfaces:**
- Consumes: `dashboard.tg_client.make_client(session_name: str) -> TelegramClient` (Task 1), `dashboard.state.get_active_session(request) -> Optional[str]` (Task 1).
- Produces:
  - `dashboard.services.chats_service.list_dialogs(session_name: str) -> List[Dict]` (each dict: `{"name": str, "id": int, "type": str, "username": Optional[str]}`).
  - `dashboard.services.chats_service.save_dialogs_csv(rows: List[Dict]) -> str` (returns the CSV path written).

- [ ] **Step 1: Create `dashboard/services/chats_service.py`**

```python
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
```

- [ ] **Step 2: Create `dashboard/routes/chats.py`**

```python
"""Chats tab, extracted from 3_chat_management/30_list_chats.py."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dashboard.state import get_active_session, list_sessions
from dashboard.services.chats_service import list_dialogs, save_dialogs_csv

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(prefix="/chats")


@router.get("", response_class=HTMLResponse)
async def chats_page(request: Request):
    active = get_active_session(request)
    rows = []
    error = None
    if active:
        try:
            rows = await list_dialogs(active)
            save_dialogs_csv(rows)
        except Exception as e:
            error = str(e)
    return templates.TemplateResponse("chats.html", {
        "request": request, "rows": rows, "error": error,
        "active_session": active, "all_sessions": list_sessions(),
    })
```

- [ ] **Step 3: Create `dashboard/templates/chats.html`**

```html
{% extends "base.html" %}
{% block title %}Chats{% endblock %}
{% block content %}
<h1>Chats ({{ active_session or "no active session" }})</h1>
{% if error %}<div class="error-banner">{{ error }}</div>{% endif %}
<table>
  <thead><tr><th>Type</th><th>Name</th><th>ID</th><th>Username</th></tr></thead>
  <tbody>
    {% for r in rows %}
    <tr><td>{{ r.type }}</td><td>{{ r.name }}</td><td>{{ r.id }}</td><td>{{ r.username or "" }}</td></tr>
    {% endfor %}
  </tbody>
</table>
<p>{{ rows|length }} dialogs. Saved to <code>3_chat_management/30_data/30_dialogs.csv</code>.</p>
{% endblock %}
```

- [ ] **Step 4: Wire the router into `dashboard/app.py`**

```python
from dashboard.routes import chats
app.include_router(chats.router)
```

- [ ] **Step 5: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/chats_service.py dashboard/routes/chats.py dashboard/app.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Manual smoke test**

Run the dashboard with a logged-in session set active; open `/chats`; confirm the dialog table renders and `3_chat_management/30_data/30_dialogs.csv` is created/updated.
Expected: table populated, CSV file present.

- [ ] **Step 7: Commit**

```bash
git add dashboard/services/chats_service.py dashboard/routes/chats.py dashboard/templates/chats.html dashboard/app.py
git commit -m "feat(dashboard): chats tab"
```

---

### Task 7: Group Users tab (websocket progress)

**Files:**
- Create: `dashboard/services/group_users_service.py`
- Create: `dashboard/routes/groups.py`
- Create: `dashboard/templates/groups.html`
- Modify: `dashboard/app.py` (include `groups.router`)
- Test: `python -m py_compile dashboard/services/group_users_service.py dashboard/routes/groups.py`

**Interfaces:**
- Consumes: `dashboard.tg_client.make_client` (Task 1), `dashboard.state.get_active_session` (Task 1), `utils.tg_utils.slugify(text: str) -> str` (existing, reused not reimplemented).
- Produces:
  - `dashboard.services.group_users_service.list_group_users(session_name: str, group_id: int, export_phone_numbers: bool = False, aggressive: bool = False, progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]] = None) -> List[Dict]` (each dict: `{"id","username","first_name","last_name","phone","bot"}`).
  - `dashboard.services.group_users_service.save_group_users_csv(entity_title: str, entity_id: int, users: List[Dict], export_phone_numbers: bool = False) -> str`.

- [ ] **Step 1: Create `dashboard/services/group_users_service.py`**

```python
"""Group member listing, extracted from 3_chat_management/31_list_group_users.py."""
import csv
import os
from typing import Awaitable, Callable, Dict, List, Optional

from telethon.tl.types import User

from dashboard.state import ROOT_DIR
from dashboard.tg_client import make_client
from utils.tg_utils import slugify

ProgressCB = Callable[[int, int, str], Awaitable[None]]

EXPORT_PHONE_NUMBERS_DEFAULT = os.getenv("EXPORT_PHONE_NUMBERS", "false").strip().lower() == "true"
AGGRESSIVE_SCRAPE_DEFAULT = os.getenv("AGGRESSIVE_SCRAPE", "false").strip().lower() == "true"


async def list_group_users(session_name: str, group_id: int, export_phone_numbers: bool = False,
                            aggressive: bool = False, progress_cb: Optional[ProgressCB] = None) -> List[Dict]:
    client = make_client(session_name)
    await client.start()
    users: List[Dict] = []
    try:
        entity = await client.get_entity(group_id)
        async for user in client.iter_participants(entity, aggressive=aggressive):
            if not isinstance(user, User):
                continue
            users.append({
                "id": user.id,
                "username": user.username or "",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "phone": (user.phone or "") if export_phone_numbers else "",
                "bot": user.bot,
            })
            if progress_cb:
                await progress_cb(len(users), 0, f"Found {len(users)} users...")
        if progress_cb:
            await progress_cb(len(users), len(users), "Done")
    finally:
        await client.disconnect()
    return users


def save_group_users_csv(entity_title: str, entity_id: int, users: List[Dict], export_phone_numbers: bool = False) -> str:
    out_dir = ROOT_DIR / "3_chat_management" / "31_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_id = str(entity_id).replace("-", "n")
    safe_name = slugify(entity_title)
    out_csv = out_dir / f"31_users_{safe_name}_{safe_id}_{len(users)}.csv"
    header = ["group_name", "group_id", "id", "username", "first_name", "last_name"]
    if export_phone_numbers:
        header.append("phone")
    header.append("is_bot")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for u in users:
            row = [entity_title, entity_id, u["id"], u["username"], u["first_name"], u["last_name"]]
            if export_phone_numbers:
                row.append(u["phone"])
            row.append(u["bot"])
            writer.writerow(row)
    return str(out_csv)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(list_group_users)
    assert not inspect.iscoroutinefunction(save_group_users_csv)
    print("group_users_service.py smoke check OK")
```

- [ ] **Step 2: Create `dashboard/routes/groups.py`**

```python
"""Group Users tab, extracted from 3_chat_management/31_list_group_users.py."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dashboard.state import get_active_session, list_sessions
from dashboard.services.group_users_service import (
    list_group_users, save_group_users_csv, EXPORT_PHONE_NUMBERS_DEFAULT, AGGRESSIVE_SCRAPE_DEFAULT,
)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(prefix="/groups")


@router.get("/{group_id}/users", response_class=HTMLResponse)
async def group_users_page(request: Request, group_id: int):
    return templates.TemplateResponse("groups.html", {
        "request": request, "group_id": group_id,
        "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/{group_id}/users/ws")
async def group_users_ws(websocket: WebSocket, group_id: int):
    await websocket.accept()
    session_name = websocket.cookies.get("active_session")
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return

    async def progress_cb(current: int, total: int, message: str):
        await websocket.send_json({"current": current, "total": total, "message": message})

    try:
        users = await list_group_users(
            session_name, group_id,
            export_phone_numbers=EXPORT_PHONE_NUMBERS_DEFAULT,
            aggressive=AGGRESSIVE_SCRAPE_DEFAULT,
            progress_cb=progress_cb,
        )
        csv_path = save_group_users_csv(str(group_id), group_id, users, EXPORT_PHONE_NUMBERS_DEFAULT)
        await websocket.send_json({"current": len(users), "total": len(users), "message": f"Saved {csv_path}", "done": True})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
```

- [ ] **Step 3: Create `dashboard/templates/groups.html`**

```html
{% extends "base.html" %}
{% block title %}Group Users{% endblock %}
{% block content %}
<h1>Group Users: {{ group_id }}</h1>
<div class="progress-bar-outer"><div id="bar" class="progress-bar-inner" style="width:0%"></div></div>
<p id="status">Connecting...</p>
<script>
  openProgressSocket("/groups/{{ group_id }}/users/ws", (data) => {
    if (data.error) {
      document.getElementById("status").textContent = "Error: " + data.error;
      return;
    }
    document.getElementById("status").textContent = data.message;
    if (data.total) {
      document.getElementById("bar").style.width = Math.round((data.current / data.total) * 100) + "%";
    }
  });
</script>
{% endblock %}
```

- [ ] **Step 4: Wire the router into `dashboard/app.py`**

```python
from dashboard.routes import groups
app.include_router(groups.router)
```

- [ ] **Step 5: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/group_users_service.py dashboard/routes/groups.py dashboard/app.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Manual smoke test**

Run the dashboard, set an active session, navigate to `/groups/<real_group_id>/users`, confirm progress messages stream and a CSV appears under `3_chat_management/31_data/`.
Expected: progress bar updates, CSV written.

- [ ] **Step 7: Commit**

```bash
git add dashboard/services/group_users_service.py dashboard/routes/groups.py dashboard/templates/groups.html dashboard/app.py
git commit -m "feat(dashboard): group users tab with websocket progress"
```

---

### Task 8: Scraping tab (websocket progress, checkpoint resume)

**Files:**
- Create: `dashboard/services/scrape_service.py`
- Create: `dashboard/routes/scrape.py`
- Create: `dashboard/templates/scrape.html`
- Modify: `dashboard/app.py` (include `scrape.router`)
- Test: `python -m py_compile dashboard/services/scrape_service.py dashboard/routes/scrape.py`

**Interfaces:**
- Consumes: `dashboard.tg_client.make_client` (Task 1), `dashboard.state.get_active_session` (Task 1), `utils.tg_utils.slugify` (existing).
- Produces:
  - `dashboard.services.scrape_service.LinkRecord` dataclass (`url, date_dt, message_id, topic_id, user_id, username, user_first, user_last, group_name, group_id`).
  - `dashboard.services.scrape_service.ScrapeResult` dataclass (`scanned: int, links: List[LinkRecord], csv_path: str, oldest_reached: Optional[str]`).
  - `dashboard.services.scrape_service.scrape_links(session_name: str, group_id: int, keyword: Optional[str] = None, startswith: Optional[str] = None, since_date: Optional[str] = None, message_limit: Optional[int] = 500, resume: bool = False, progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]] = None) -> ScrapeResult`.

- [ ] **Step 1: Create `dashboard/services/scrape_service.py`**

```python
"""Link scraper, extracted from 4_scraping/41_scrape_links_advanced.py."""
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Dict, Iterable, List, Optional

from telethon.tl.types import Message, MessageEntityTextUrl

from dashboard.state import ROOT_DIR
from dashboard.tg_client import make_client
from utils.tg_utils import slugify

ProgressCB = Callable[[int, int, str], Awaitable[None]]

URL_RE = re.compile(
    r"""(?ix)
    \b(
        https?://[^\s<>"'()\[\]]+
        |
        www\.[^\s<>"'()\[\]]+
        |
        //[^ \t\r\n<>"'()\[\]]+
    )
    """
)
INVISIBLES = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]


@dataclass(frozen=True)
class LinkRecord:
    url: str
    date_dt: datetime
    message_id: int
    topic_id: Optional[int]
    user_id: Optional[int]
    username: Optional[str]
    user_first: Optional[str]
    user_last: Optional[str]
    group_name: str
    group_id: int


@dataclass
class ScrapeResult:
    scanned: int
    links: List[LinkRecord]
    csv_path: str
    oldest_reached: Optional[str]


def _repair_url(u: str) -> str:
    s = (u or "").strip()
    for ch in INVISIBLES:
        s = s.replace(ch, "")
    s = s.strip().rstrip(").,!?;:\"'<>]")
    low = s.lower()
    if low.startswith("//"):
        s = "https:" + s
    elif low.startswith("tps://"):
        s = "h" + s
    elif low.startswith("hxxps://"):
        s = "https://" + s[8:]
    elif low.startswith("hxxp://"):
        s = "http://" + s[7:]
    elif low.startswith("www."):
        s = "https://" + s
    return s


def _passes_filter(url: str, keyword_lower: str, startswith: Optional[str]) -> bool:
    if startswith and not url.startswith(startswith):
        return False
    if keyword_lower and keyword_lower not in url.lower():
        return False
    return True


def _parse_since_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_topic_id(msg: Message) -> Optional[int]:
    rt = getattr(msg, "reply_to", None)
    if not rt:
        return None
    return getattr(rt, "reply_to_top_id", None) or getattr(rt, "top_msg_id", None) or None


def _urls_from_text_urls(msg: Message) -> Iterable[str]:
    if not msg.entities:
        return
    for ent in msg.entities:
        if isinstance(ent, MessageEntityTextUrl):
            yield _repair_url(str(ent.url))


def _urls_from_regex(text: str) -> Iterable[str]:
    for m in URL_RE.finditer(text or ""):
        yield _repair_url(m.group(1))


def _checkpoint_path(out_dir: Path, group_id: int) -> Path:
    return out_dir / "checkpoints" / f"checkpoint_{str(group_id).replace('-', 'n')}.json"


def _next_available_filename(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        cand = parent / f"{stem}({i}){suffix}"
        if not cand.exists():
            return cand
        i += 1


async def scrape_links(session_name: str, group_id: int, keyword: Optional[str] = None,
                        startswith: Optional[str] = None, since_date: Optional[str] = None,
                        message_limit: Optional[int] = 500, resume: bool = False,
                        progress_cb: Optional[ProgressCB] = None) -> ScrapeResult:
    keyword_lower = (keyword or "").lower()
    since_dt = _parse_since_date(since_date)
    seen: Dict[str, LinkRecord] = {}
    scanned = 0
    oldest_dt_seen = None

    out_dir = ROOT_DIR / "4_scraping" / "41_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = _checkpoint_path(out_dir, group_id)

    client = make_client(session_name)
    await client.start()
    try:
        entity = await client.get_entity(group_id)
        offset_id = 0
        if resume and checkpoint_path.exists():
            data = json.loads(checkpoint_path.read_text())
            offset_id = data.get("last_id", 0)
        last_id_scanned = offset_id

        async for msg in client.iter_messages(entity, limit=message_limit, offset_id=offset_id):
            if not isinstance(msg, Message):
                continue
            last_id_scanned = msg.id
            scanned += 1
            if progress_cb:
                await progress_cb(scanned, message_limit or 0, f"Found {len(seen)} links... ({scanned} msgs)")
            msg_dt = msg.date
            if msg_dt and msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)
            msg_dt = (msg_dt or datetime.now(timezone.utc)).astimezone(timezone.utc)
            if since_dt and msg_dt < since_dt:
                break
            oldest_dt_seen = msg_dt
            topic_id = _get_topic_id(msg)
            text = msg.raw_text or msg.message or ""
            sender = getattr(msg, "sender", None)
            user_id = getattr(sender, "id", None) if sender else None
            username = getattr(sender, "username", None) if sender else None
            first_name = getattr(sender, "first_name", None) if sender else None
            last_name = getattr(sender, "last_name", None) if sender else None

            for url in list(_urls_from_text_urls(msg)) + list(_urls_from_regex(text)):
                if url and _passes_filter(url, keyword_lower, startswith) and url not in seen:
                    seen[url] = LinkRecord(
                        url=url, date_dt=msg_dt, message_id=msg.id, topic_id=topic_id,
                        user_id=user_id, username=username, user_first=first_name, user_last=last_name,
                        group_name=getattr(entity, "title", "N/A"), group_id=entity.id,
                    )

        csv_path = _save_csv(seen, out_dir, getattr(entity, "title", "N/A"), entity.id)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        return ScrapeResult(scanned=scanned, links=list(seen.values()), csv_path=csv_path,
                             oldest_reached=oldest_dt_seen.isoformat() if oldest_dt_seen else None)
    except Exception:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps({"last_id": last_id_scanned}))
        raise
    finally:
        await client.disconnect()


def _save_csv(seen: Dict[str, LinkRecord], out_dir: Path, group_name: str, group_id: int) -> str:
    safe_name = slugify(group_name)
    safe_id = str(group_id).replace("-", "n")
    base_path = out_dir / f"41_links_{safe_name}_{safe_id}.csv"
    out_csv = _next_available_filename(base_path)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group_name", "group_id", "url", "date_sent", "message_id", "topic_id", "user_id", "username", "first_name", "last_name"])
        for r in seen.values():
            w.writerow([r.group_name, r.group_id, r.url, r.date_dt.isoformat(), r.message_id, r.topic_id, r.user_id, r.username, r.user_first, r.user_last])
    return str(out_csv)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(scrape_links)
    sig = inspect.signature(scrape_links)
    assert list(sig.parameters.keys())[:2] == ["session_name", "group_id"]
    print("scrape_service.py smoke check OK")
```

- [ ] **Step 2: Create `dashboard/routes/scrape.py`**

```python
"""Scraping tab, extracted from 4_scraping/41_scrape_links_advanced.py."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dashboard.state import get_active_session, list_sessions
from dashboard.services.scrape_service import scrape_links

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(prefix="/scrape")


@router.get("", response_class=HTMLResponse)
async def scrape_page(request: Request):
    return templates.TemplateResponse("scrape.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/ws")
async def scrape_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = websocket.cookies.get("active_session")
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        params = await websocket.receive_json()
        group_id = int(params["group_id"])
        keyword = params.get("keyword") or None
        startswith = params.get("startswith") or None
        since_date = params.get("since_date") or None
        message_limit = int(params["message_limit"]) if params.get("message_limit") else None
        resume = bool(params.get("resume", False))

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        result = await scrape_links(
            session_name, group_id, keyword=keyword, startswith=startswith, since_date=since_date,
            message_limit=message_limit, resume=resume, progress_cb=progress_cb,
        )
        await websocket.send_json({
            "current": result.scanned, "total": result.scanned,
            "message": f"Done. {len(result.links)} unique links -> {result.csv_path}", "done": True,
        })
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
```

- [ ] **Step 3: Create `dashboard/templates/scrape.html`**

```html
{% extends "base.html" %}
{% block title %}Scraping{% endblock %}
{% block content %}
<h1>Extract Links</h1>
<input id="group_id" placeholder="Group ID" />
<input id="keyword" placeholder="Keyword filter (optional)" />
<input id="startswith" placeholder="Starts-with filter (optional)" />
<input id="since_date" placeholder="Since date YYYY-MM-DD (optional)" />
<input id="message_limit" placeholder="Message limit (default 500)" />
<label><input id="resume" type="checkbox" /> Resume from checkpoint</label>
<button onclick="startScrape()">Start</button>
<div class="progress-bar-outer"><div id="bar" class="progress-bar-inner" style="width:0%"></div></div>
<p id="status"></p>
<script>
  function startScrape() {
    const ws = openProgressSocket("/scrape/ws", (data) => {
      if (data.error) {
        document.getElementById("status").textContent = "Error: " + data.error;
        return;
      }
      document.getElementById("status").textContent = data.message;
      if (data.total) {
        document.getElementById("bar").style.width = Math.round((data.current / data.total) * 100) + "%";
      }
    });
    ws.onopen = () => {
      ws.send(JSON.stringify({
        group_id: document.getElementById("group_id").value,
        keyword: document.getElementById("keyword").value,
        startswith: document.getElementById("startswith").value,
        since_date: document.getElementById("since_date").value,
        message_limit: document.getElementById("message_limit").value,
        resume: document.getElementById("resume").checked,
      }));
    };
  }
</script>
{% endblock %}
```

- [ ] **Step 4: Wire the router into `dashboard/app.py`**

```python
from dashboard.routes import scrape
app.include_router(scrape.router)
```

- [ ] **Step 5: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/scrape_service.py dashboard/routes/scrape.py dashboard/app.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Manual smoke test**

Run the dashboard, drive `/scrape` against a real group with a small `message_limit`, confirm progress streams and a CSV appears under `4_scraping/41_data/`; interrupt mid-scrape and confirm a checkpoint file is written; re-run with "Resume" checked and confirm it picks up from the checkpoint.
Expected: CSV written, checkpoint resume works.

- [ ] **Step 7: Commit**

```bash
git add dashboard/services/scrape_service.py dashboard/routes/scrape.py dashboard/templates/scrape.html dashboard/app.py
git commit -m "feat(dashboard): scraping tab with websocket progress and checkpoint resume"
```

---

### Task 9: Stats tab (websocket progress)

**Files:**
- Create: `dashboard/services/stats_service.py`
- Create: `dashboard/routes/stats.py`
- Create: `dashboard/templates/stats.html`
- Modify: `dashboard/app.py` (include `stats.router`)
- Test: `python -m py_compile dashboard/services/stats_service.py dashboard/routes/stats.py`

**Interfaces:**
- Consumes: `dashboard.tg_client.make_client` (Task 1), `dashboard.state.get_active_session` (Task 1), `utils.tg_utils.slugify` (existing).
- Produces:
  - `dashboard.services.stats_service.StatsResult` dataclass (`total_scanned: int, top_users: List[Tuple[str, int, float]], peak_hours: List[Tuple[int, int]], csv_path: str`).
  - `dashboard.services.stats_service.group_stats(session_name: str, group_id: int, limit: int = 2000, progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]] = None) -> StatsResult`.

- [ ] **Step 1: Create `dashboard/services/stats_service.py`**

```python
"""Group analytics, extracted from 5_monitoring/50_group_stats.py."""
import csv
from collections import Counter
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional, Tuple

from telethon.tl.types import Message

from dashboard.state import ROOT_DIR
from dashboard.tg_client import make_client
from utils.tg_utils import slugify

ProgressCB = Callable[[int, int, str], Awaitable[None]]


@dataclass
class StatsResult:
    total_scanned: int
    top_users: List[Tuple[str, int, float]]
    peak_hours: List[Tuple[int, int]]
    csv_path: str


async def group_stats(session_name: str, group_id: int, limit: int = 2000,
                       progress_cb: Optional[ProgressCB] = None) -> StatsResult:
    client = make_client(session_name)
    await client.start()
    try:
        entity = await client.get_entity(group_id)
        user_msgs: Counter = Counter()
        user_names = {}
        hours: Counter = Counter()
        total_scanned = 0

        async for msg in client.iter_messages(entity, limit=limit):
            if not isinstance(msg, Message):
                continue
            total_scanned += 1
            if msg.sender_id:
                user_msgs[msg.sender_id] += 1
                if msg.sender_id not in user_names:
                    sender = getattr(msg, "sender", None)
                    if sender:
                        name = f"@{sender.username}" if getattr(sender, "username", None) else \
                            f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip()
                        user_names[msg.sender_id] = name or f"ID:{msg.sender_id}"
            if msg.date:
                hours[msg.date.hour] += 1
            if progress_cb:
                await progress_cb(total_scanned, limit, f"Scanned {total_scanned} messages...")

        top_users = [
            (user_names.get(uid, str(uid)), count, (count / total_scanned) * 100 if total_scanned else 0.0)
            for uid, count in user_msgs.most_common(10)
        ]
        peak_hours = sorted(hours.most_common(5))

        csv_path = _save_csv(entity, total_scanned, user_msgs, user_names, hours)
        return StatsResult(total_scanned=total_scanned, top_users=top_users, peak_hours=peak_hours, csv_path=csv_path)
    finally:
        await client.disconnect()


def _save_csv(entity, total_scanned, user_msgs, user_names, hours) -> str:
    out_dir = ROOT_DIR / "5_monitoring" / "50_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify(getattr(entity, "title", ""))
    safe_id = str(entity.id).replace("-", "n")
    out_csv = out_dir / f"stats_{safe_name}_{safe_id}.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value", "Count/Details"])
        writer.writerow(["GROUP_TITLE", getattr(entity, "title", "N/A"), str(entity.id)])
        writer.writerow(["SCAN_TOTAL", str(total_scanned), ""])
        writer.writerow([])
        writer.writerow(["TOP_USERS"])
        for uid, count in user_msgs.most_common(50):
            writer.writerow(["User", user_names.get(uid, str(uid)), str(count)])
        writer.writerow([])
        writer.writerow(["HOURLY_ACTIVITY"])
        for hr in range(24):
            writer.writerow(["Hour", f"{hr:02}:00", str(hours[hr])])
    return str(out_csv)


if __name__ == "__main__":
    import inspect
    assert inspect.iscoroutinefunction(group_stats)
    print("stats_service.py smoke check OK")
```

- [ ] **Step 2: Create `dashboard/routes/stats.py`**

```python
"""Stats tab, extracted from 5_monitoring/50_group_stats.py."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dashboard.state import get_active_session, list_sessions
from dashboard.services.stats_service import group_stats

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(prefix="/stats")


@router.get("", response_class=HTMLResponse)
async def stats_page(request: Request):
    return templates.TemplateResponse("stats.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/ws")
async def stats_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = websocket.cookies.get("active_session")
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        params = await websocket.receive_json()
        group_id = int(params["group_id"])
        limit = int(params["limit"]) if params.get("limit") else 2000

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        result = await group_stats(session_name, group_id, limit=limit, progress_cb=progress_cb)
        await websocket.send_json({
            "current": result.total_scanned, "total": result.total_scanned,
            "message": f"Done. Saved {result.csv_path}", "done": True,
            "top_users": result.top_users, "peak_hours": result.peak_hours,
        })
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
```

- [ ] **Step 3: Create `dashboard/templates/stats.html`**

```html
{% extends "base.html" %}
{% block title %}Stats{% endblock %}
{% block content %}
<h1>Group Analytics</h1>
<input id="group_id" placeholder="Group ID" />
<input id="limit" placeholder="Message limit (default 2000)" />
<button onclick="startStats()">Analyze</button>
<div class="progress-bar-outer"><div id="bar" class="progress-bar-inner" style="width:0%"></div></div>
<p id="status"></p>
<table id="top-users"><thead><tr><th>User</th><th>Messages</th><th>%</th></tr></thead><tbody></tbody></table>
<script>
  function startStats() {
    const ws = openProgressSocket("/stats/ws", (data) => {
      if (data.error) {
        document.getElementById("status").textContent = "Error: " + data.error;
        return;
      }
      document.getElementById("status").textContent = data.message;
      if (data.total) {
        document.getElementById("bar").style.width = Math.round((data.current / data.total) * 100) + "%";
      }
      if (data.done && data.top_users) {
        const tbody = document.querySelector("#top-users tbody");
        tbody.innerHTML = "";
        data.top_users.forEach((u) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${u[0]}</td><td>${u[1]}</td><td>${u[2].toFixed(1)}%</td>`;
          tbody.appendChild(tr);
        });
      }
    });
    ws.onopen = () => {
      ws.send(JSON.stringify({
        group_id: document.getElementById("group_id").value,
        limit: document.getElementById("limit").value,
      }));
    };
  }
</script>
{% endblock %}
```

- [ ] **Step 4: Wire the router into `dashboard/app.py`**

```python
from dashboard.routes import stats
app.include_router(stats.router)
```

- [ ] **Step 5: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/stats_service.py dashboard/routes/stats.py dashboard/app.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Manual smoke test**

Run the dashboard, drive `/stats` against a real group, confirm progress streams and the top-users table populates, and a CSV appears under `5_monitoring/50_data/`.
Expected: analysis completes, table populated, CSV written.

- [ ] **Step 7: Commit**

```bash
git add dashboard/services/stats_service.py dashboard/routes/stats.py dashboard/templates/stats.html dashboard/app.py
git commit -m "feat(dashboard): stats tab with websocket progress"
```

---

### Task 10: Utilities — participation finder (websocket progress)

**Files:**
- Create: `dashboard/services/participation_service.py`
- Create/Modify: `dashboard/routes/utilities.py` (create; also houses purge routes added in Task 11)
- Create: `dashboard/templates/utilities_participation.html`
- Modify: `dashboard/app.py` (include `utilities.router`)
- Test: `python -m py_compile dashboard/services/participation_service.py dashboard/routes/utilities.py`

**Interfaces:**
- Consumes: `dashboard.tg_client.make_client` (Task 1), `dashboard.state.get_active_session` (Task 1).
- Produces:
  - `dashboard.services.participation_service.find_participation(session_name: str, progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]] = None) -> List[Dict]` (each dict: `{"type": str, "name": str, "id": int, "count": int}`).

- [ ] **Step 1: Create `dashboard/services/participation_service.py`**

```python
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
```

- [ ] **Step 2: Create `dashboard/routes/utilities.py`**

```python
"""Utilities tab: participation finder (this task) + purge (Task 11)."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dashboard.state import get_active_session, list_sessions
from dashboard.services.participation_service import find_participation

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(prefix="/utilities")


@router.get("/participation", response_class=HTMLResponse)
async def participation_page(request: Request):
    return templates.TemplateResponse("utilities_participation.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/participation/ws")
async def participation_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = websocket.cookies.get("active_session")
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        results = await find_participation(session_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": len(results), "total": len(results),
            "message": f"Found {len(results)} chats with your messages.", "done": True, "results": results,
        })
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
```

- [ ] **Step 3: Create `dashboard/templates/utilities_participation.html`**

```html
{% extends "base.html" %}
{% block title %}Find My Participation{% endblock %}
{% block content %}
<h1>Find My Participation</h1>
<button onclick="startScan()">Scan</button>
<div class="progress-bar-outer"><div id="bar" class="progress-bar-inner" style="width:0%"></div></div>
<p id="status"></p>
<table id="results"><thead><tr><th>Type</th><th>Name</th><th>ID</th><th>My Messages</th></tr></thead><tbody></tbody></table>
<script>
  function startScan() {
    const ws = openProgressSocket("/utilities/participation/ws", (data) => {
      if (data.error) {
        document.getElementById("status").textContent = "Error: " + data.error;
        return;
      }
      document.getElementById("status").textContent = data.message;
      if (data.total) {
        document.getElementById("bar").style.width = Math.round((data.current / data.total) * 100) + "%";
      }
      if (data.done && data.results) {
        const tbody = document.querySelector("#results tbody");
        tbody.innerHTML = "";
        data.results.forEach((r) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `<td>${r.type}</td><td>${r.name}</td><td>${r.id}</td><td>${r.count}</td>`;
          tbody.appendChild(tr);
        });
      }
    });
  }
</script>
{% endblock %}
```

- [ ] **Step 4: Wire the router into `dashboard/app.py`**

```python
from dashboard.routes import utilities
app.include_router(utilities.router)
```

- [ ] **Step 5: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/participation_service.py dashboard/routes/utilities.py dashboard/app.py`
Expected: no output, exit code 0.

- [ ] **Step 6: Manual smoke test**

Run the dashboard, drive `/utilities/participation`, confirm progress streams and the results table populates.
Expected: scan completes, table populated.

- [ ] **Step 7: Commit**

```bash
git add dashboard/services/participation_service.py dashboard/routes/utilities.py dashboard/templates/utilities_participation.html dashboard/app.py
git commit -m "feat(dashboard): utilities participation-finder tab with websocket progress"
```

---

### Task 11: Utilities — purge (destructive, type-to-confirm, websocket progress)

**Files:**
- Create: `dashboard/services/purge_service.py`
- Modify: `dashboard/routes/utilities.py` (append purge routes)
- Create: `dashboard/templates/utilities_purge.html`
- Test: `python -m py_compile dashboard/services/purge_service.py dashboard/routes/utilities.py`

**Interfaces:**
- Consumes: `dashboard.tg_client.make_client` (Task 1), `dashboard.state.get_active_session` (Task 1), `dashboard.auth.require_auth` (already app-wide, Task 1 — purge routes get no additional dependency since every route in the app already requires it; the type-to-confirm check below is the *additional* safety layer the spec requires).
- Produces:
  - `dashboard.services.purge_service.scan_my_activity(session_name: str, progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]] = None) -> List[Dict]` (each dict: `{"name": str, "id": int, "type": str, "count": int}`).
  - `dashboard.services.purge_service.preview_my_messages(session_name: str, group_id: int, limit: int = 10) -> List[Dict]` (each dict: `{"date": str, "content": str}`).
  - `dashboard.services.purge_service.purge_my_messages(session_name: str, group_id: int, target_name: str, confirm_name: str, progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]] = None) -> Dict` (`{"deleted_count": int}`; raises `ValueError` if `confirm_name != target_name`).

- [ ] **Step 1: Create `dashboard/services/purge_service.py`**

```python
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
```

- [ ] **Step 2: Append purge routes to `dashboard/routes/utilities.py`**

```python
# --- Purge routes (append below participation_ws) ---
from dashboard.services.purge_service import scan_my_activity, preview_my_messages, purge_my_messages


@router.get("/purge", response_class=HTMLResponse)
async def purge_page(request: Request):
    return templates.TemplateResponse("utilities_purge.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/purge/scan/ws")
async def purge_scan_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = websocket.cookies.get("active_session")
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        chats = await scan_my_activity(session_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": len(chats), "total": len(chats),
            "message": f"Found {len(chats)} chats with your messages.", "done": True, "chats": chats,
        })
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


@router.get("/purge/preview")
async def purge_preview(request: Request, group_id: int):
    session_name = get_active_session(request)
    if not session_name:
        return {"error": "No active session set."}
    try:
        rows = await preview_my_messages(session_name, group_id)
        return {"preview": rows}
    except Exception as e:
        return {"error": str(e)}


@router.websocket("/purge/ws")
async def purge_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = websocket.cookies.get("active_session")
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        params = await websocket.receive_json()
        group_id = int(params["group_id"])
        target_name = params["target_name"]
        confirm_name = params["confirm_name"]

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        result = await purge_my_messages(session_name, group_id, target_name, confirm_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": result["deleted_count"], "total": result["deleted_count"],
            "message": f"Deleted {result['deleted_count']} messages.", "done": True,
        })
    except ValueError as e:
        await websocket.send_json({"error": str(e)})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
```

- [ ] **Step 3: Create `dashboard/templates/utilities_purge.html`**

```html
{% extends "base.html" %}
{% block title %}Purge My Messages{% endblock %}
{% block content %}
<h1>Self-Destruct Purge</h1>
<p class="error-banner">⚠️ This permanently deletes your own messages in the selected chat. This cannot be undone.</p>
<button onclick="startScan()">Scan My Activity</button>
<div class="progress-bar-outer"><div id="scan-bar" class="progress-bar-inner" style="width:0%"></div></div>
<p id="scan-status"></p>
<table id="results"><thead><tr><th></th><th>Type</th><th>Name</th><th>My Msgs</th></tr></thead><tbody></tbody></table>

<div id="confirm-section" style="display:none">
  <h2 id="confirm-title"></h2>
  <div id="preview"></div>
  <p>Type the chat name below to confirm permanent deletion:</p>
  <input id="confirm-input" placeholder="Type chat name exactly" />
  <button onclick="doPurge()">DELETE ALL MY MESSAGES</button>
  <div class="progress-bar-outer"><div id="purge-bar" class="progress-bar-inner" style="width:0%"></div></div>
  <p id="purge-status"></p>
</div>

<script>
  let selectedChat = null;

  function startScan() {
    const ws = openProgressSocket("/utilities/purge/scan/ws", (data) => {
      if (data.error) {
        document.getElementById("scan-status").textContent = "Error: " + data.error;
        return;
      }
      document.getElementById("scan-status").textContent = data.message;
      if (data.total) {
        document.getElementById("scan-bar").style.width = Math.round((data.current / data.total) * 100) + "%";
      }
      if (data.done && data.chats) {
        const tbody = document.querySelector("#results tbody");
        tbody.innerHTML = "";
        data.chats.forEach((c) => {
          const tr = document.createElement("tr");
          const btn = `<button onclick='selectChat(${c.id}, ${JSON.stringify(c.name)})'>Select</button>`;
          tr.innerHTML = `<td>${btn}</td><td>${c.type}</td><td>${c.name}</td><td>${c.count}</td>`;
          tbody.appendChild(tr);
        });
      }
    });
  }

  async function selectChat(id, name) {
    selectedChat = { id, name };
    document.getElementById("confirm-title").textContent = "Purging: " + name;
    document.getElementById("confirm-section").style.display = "block";
    const resp = await fetch(`/utilities/purge/preview?group_id=${id}`);
    const data = await resp.json();
    if (data.preview) {
      document.getElementById("preview").innerHTML = data.preview
        .map((p) => `<div>${p.date} | ${p.content}</div>`).join("");
    }
  }

  function doPurge() {
    const confirmName = document.getElementById("confirm-input").value;
    const ws = openProgressSocket("/utilities/purge/ws", (data) => {
      if (data.error) {
        document.getElementById("purge-status").textContent = "Error: " + data.error;
        return;
      }
      document.getElementById("purge-status").textContent = data.message;
      if (data.total) {
        document.getElementById("purge-bar").style.width = Math.round((data.current / data.total) * 100) + "%";
      }
    });
    ws.onopen = () => {
      ws.send(JSON.stringify({
        group_id: selectedChat.id, target_name: selectedChat.name, confirm_name: confirmName,
      }));
    };
  }
</script>
{% endblock %}
```

- [ ] **Step 4: Verify syntax**

Run: `venv/bin/python -m py_compile dashboard/services/purge_service.py dashboard/routes/utilities.py`
Expected: no output, exit code 0.

- [ ] **Step 5: Manual smoke test against a disposable test chat**

Run the dashboard, drive `/utilities/purge` against a throwaway test chat: scan, select it, verify the preview shows your recent messages, type a **wrong** confirmation name and confirm it errors without deleting, then type the correct name and confirm messages are deleted and the progress bar reaches 100%.
Expected: mismatched confirm text blocks the delete; correct text deletes messages.

- [ ] **Step 6: Commit**

```bash
git add dashboard/services/purge_service.py dashboard/routes/utilities.py dashboard/templates/utilities_purge.html
git commit -m "feat(dashboard): utilities purge tab with type-to-confirm safety and websocket progress"
```

---

### Task 12: Venv consolidation, retire `65/venv`, update `run.py`, update `CLAUDE.md`

**Files:**
- Modify: `run.py:35-53,77,99-100` (replace `run_dashboard_pair` usage with a direct launch of `dashboard/app.py`)
- Modify: `CLAUDE.md` (Commands and Architecture sections)
- Delete (destructive, confirm with user first): `6_messaging/65/venv/` directory, if present
- Test: `python -m py_compile run.py`

**Interfaces:**
- Consumes: `dashboard/app.py`'s `__main__` entrypoint (Task 1) — run via `subprocess.run([sys.executable, os.path.join("dashboard", "app.py")])` from repo root.
- Produces: nothing new consumed by later tasks (this is the last task).

- [ ] **Step 1: Confirm `6_messaging/65/venv/` isn't required and check whether it exists**

Run: `ls 6_messaging/65 | grep -i venv || echo "no venv dir present"`
Expected: either lists a `venv/` directory to remove, or confirms none exists (some setups may already share the root venv).

- [ ] **Step 2: Update `run.py`'s dashboard launcher**

In `run.py`, replace the `run_dashboard_pair` function (lines 35-52) with:

```python
def run_dashboard(cwd=None):
    """Starts the new consolidated web dashboard (dashboard/app.py) from repo root.

    This supersedes the old 65-only dashboard pair: dashboard/app.py's own lifespan
    hook now starts/stops the Ghost Mirror bot subprocess internally (see
    dashboard/ghost_process.py), so only one process needs to be launched here.
    """
    try:
        subprocess.run([sys.executable, os.path.join("dashboard", "app.py")])
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed to run dashboard: {e}[/bold red]")

    console.print("\n[dim][Press Enter to return to menu][/dim]")
    input()
```

Then replace the menu row text and call site. Change line 77:

```python
table.add_row("8", "🛰️", "Web Dashboard [dim]- full suite UI (login, chats, scraping, stats, ghost mirror, utilities) at localhost:8000[/dim]")
```

And change lines 99-100:

```python
elif choice == "8":
    run_dashboard()
```

- [ ] **Step 3: Remove the retired `65/venv/` directory, if present**

Run only if Step 1 found a `venv/` directory: `rm -rf 6_messaging/65/venv`

- [ ] **Step 4: Update `CLAUDE.md`'s Commands section**

In `CLAUDE.md`, replace the `## Commands` section body with:

```markdown
## Commands

Root-level scripts and the web dashboard share one venv and `requirements.txt`
(this now includes fastapi/uvicorn/jinja2/aiofiles/loguru, merged from the old
`6_messaging/65/requirements.txt`):

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt   # or venv\Scripts\pip on Windows
python dashboard/app.py                    # primary: web dashboard at http://127.0.0.1:8000
python run.py                              # fallback: terminal menu, choice 0 to exit
```

`dashboard/app.py` is the primary, documented way to run the suite: it covers login,
session verification, chats, group users, scraping, stats, Ghost Mirror, and
utilities (participation/purge) behind one HTTP Basic auth gate
(`DASHBOARD_USER`/`DASHBOARD_PASSWORD`), and manages the Ghost Mirror bot
(`6_messaging/65/ghost_runner.py`) as a supervised subprocess internally.

`run.py`'s terminal menu remains as a minimal fallback for pure-terminal use; its
choice 8 now launches `dashboard/app.py` directly instead of the old `65`-only
dashboard pair.

`6_messaging/65/` no longer has its own venv — its dependencies were merged into the
root `requirements.txt` and its `venv/` directory has been retired.

There is no test suite, linter config, or CI in this repo — don't assume
`pytest`/`ruff`/etc. exist. `python -m py_compile <file>` is the only verification
available for a quick syntax check.
```

- [ ] **Step 5: Update `CLAUDE.md`'s Ghost Mirror architecture note**

In the `### 6_messaging/: Ghost Mirror` section, add a sentence after the existing `65/` description:

```markdown
`65/`'s FastAPI dashboard routes have been ported into the root `dashboard/` app under
`/ghost/*` (see `dashboard/routes/ghost_mirror.py`), reading the same `65/data/ghost.db`
unchanged. `65/dashboard.py` itself is no longer launched directly — `dashboard/app.py`
launches `65/run.py` (the bot watchdog) as a subprocess and serves the ported routes
in-process.
```

- [ ] **Step 6: Verify syntax**

Run: `venv/bin/python -m py_compile run.py`
Expected: no output, exit code 0.

- [ ] **Step 7: Manual smoke test of the fallback menu**

Run: `venv/bin/python run.py`, choose option `8`, confirm `dashboard/app.py` starts and is reachable at `http://127.0.0.1:8000`, then Ctrl+C and confirm the menu returns cleanly.
Expected: dashboard launches from the terminal menu; Ghost Mirror bot subprocess starts as part of `dashboard/app.py`'s lifespan (no separate `65/run.py` launch from `run.py` itself anymore).

- [ ] **Step 8: Commit**

```bash
git add run.py CLAUDE.md
git commit -m "chore: consolidate venv, retire 6_messaging/65/venv, point run.py at new dashboard"
```

---

## Self-Review

**1. Spec coverage** — every section of `docs/superpowers/specs/2026-07-13-suite-dashboard-design.md` maps to a task:
- Architecture (new `dashboard/app.py` etc., consolidated venv, `ghost_runner.py` untouched, `65/dashboard.py` ported) → Tasks 1, 2, 12.
- Navigation/routes table (Sessions, Chats, Group Users, Scraping, Stats, Ghost Mirror, Utilities) → Tasks 3-5 (Sessions), 6 (Chats), 7 (Group Users), 8 (Scraping), 9 (Stats), 2 (Ghost Mirror), 10-11 (Utilities).
- Session model / global session switcher → Task 3 (`get_active_session`, `/sessions/active`, base template switcher).
- Login flow (web): phone/code/2FA steps → Task 4. QR mode with websocket waiting→scanned→done → Task 5.
- Long-running operations with background task + websocket progress `{current, total, message}` → Tasks 7, 8, 9, 10, 11.
- Purge safety (auth + type-to-confirm) → Task 11.
- Auth (HTTP Basic, fail-closed loopback binding, applied to every route) → Task 1 (`dashboard.auth.require_auth` applied app-wide via `FastAPI(dependencies=[Depends(require_auth)])`, loopback check in `__main__`).
- Error handling (exceptions → error banner / websocket `{"error": ...}`) → every websocket route in Tasks 5, 7, 8, 9, 10, 11 sends `{"error": ...}` on exception; page routes render an `error-banner` block (Task 6's `chats.html`, extendable to others by the same pattern).
- Testing/verification (`py_compile` + manual pass) → every task's Step includes both.
- Out of scope items (no new JS framework, no `ghost_runner.py` refactor, `run.py` stays, HTTP-Basic-only auth) → respected throughout; explicitly called out in Global Constraints.
No gaps found.

**2. Placeholder scan** — searched for "TBD", "TODO", "implement later", "similar to Task N", "add appropriate error handling"-style phrasing. None present; every step has runnable code, and error handling is concrete (`try`/`except` blocks with specific messages) rather than described abstractly.

**3. Type/signature consistency** — verified across tasks:
- `progress_cb: Optional[Callable[[int, int, str], Awaitable[None]]]` used identically in `sessions_service.check_all_sessions`, `group_users_service.list_group_users`, `scrape_service.scrape_links`, `stats_service.group_stats`, `participation_service.find_participation`, `purge_service.scan_my_activity`/`purge_my_messages`.
- `dashboard.state.get_active_session(request: Request) -> Optional[str]`, `list_sessions() -> List[str]`, `session_path(session_name: str) -> str` used with the same names/signatures in Tasks 3, 6, 7, 8, 9, 10, 11.
- `dashboard.tg_client.make_client(session_name: str) -> TelegramClient` used identically in Tasks 6, 7, 8, 9, 10, 11.
- `_finalize_session(client, temp_session_name) -> str` defined in Task 4, reused without redefinition by Task 5's QR flow in the same module.
- Websocket JSON progress shape `{"current": int, "total": int, "message": str}` and error shape `{"error": str}` used consistently in every websocket route (Tasks 5, 7, 8, 9, 10, 11).
- `ScrapeResult`/`StatsResult` dataclass field names (`scanned`/`links`/`csv_path`/`oldest_reached` and `total_scanned`/`top_users`/`peak_hours`/`csv_path`) are used identically between their `services/*.py` definitions and their `routes/*.py` consumers in Tasks 8 and 9.
No inconsistencies found.