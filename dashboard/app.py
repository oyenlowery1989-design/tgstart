"""Root FastAPI app: auth, static/template mounts, Ghost Mirror subprocess lifespan."""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
import uvicorn

from dashboard.auth import require_auth, DASHBOARD_PASSWORD
from dashboard.csrf import COOKIE_NAME as CSRF_COOKIE_NAME, new_token as new_csrf_token
from dashboard.ghost_process import start_ghost_bot, stop_ghost_bot
from dashboard.bot_reply_process import start_bot_reply, stop_bot_reply
from dashboard.state import FRONTEND_DIST, FRONTEND_AVAILABLE


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot_proc = start_ghost_bot()
    reply_handle = start_bot_reply()
    try:
        yield
    finally:
        stop_ghost_bot(bot_proc)
        await stop_bot_reply(reply_handle)


app = FastAPI(title="Telegram Suite Dashboard", dependencies=[Depends(require_auth)], lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.middleware("http")
async def ensure_csrf_cookie(request, call_next):
    """Guarantees every browser tab has a CSRF token before it can submit
    anything — pages read it back via `document.cookie` (fetch header) or a
    hidden form field, see dashboard/csrf.py."""
    response = await call_next(request)
    if CSRF_COOKIE_NAME not in request.cookies:
        response.set_cookie(CSRF_COOKIE_NAME, new_csrf_token(), samesite="strict", httponly=False)
    return response

from dashboard.routes import ghost_mirror, sessions, chats, groups, scrape, stats, utilities, bot_reply
app.include_router(ghost_mirror.router)
app.include_router(sessions.router)
app.include_router(chats.router)
app.include_router(groups.router)
app.include_router(scrape.router)
app.include_router(stats.router)
app.include_router(stats.api_router)
app.include_router(utilities.router)
app.include_router(bot_reply.router)

if FRONTEND_AVAILABLE:
    app.mount("/app/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend-assets")

    @app.get("/app")
    @app.get("/app/{full_path:path}")
    async def serve_frontend(full_path: str = ""):
        from fastapi.responses import FileResponse
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    print(f"[dashboard] {FRONTEND_DIST} not found — run 'npm run build' in frontend/ "
          "to enable the new UI at /app. Falling back to the classic dashboard only.")


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
