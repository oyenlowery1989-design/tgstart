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

from dashboard.auth import (
    DASHBOARD_PASSWORD,
    DASHBOARD_PUBLIC_ORIGIN,
    is_secure_request,
    remote_binding_has_https_origin,
    require_auth,
)
from dashboard.csrf import COOKIE_NAME as CSRF_COOKIE_NAME, new_token as new_csrf_token
from dashboard.ghost_process import stop_ghost_bot
from dashboard.bot_reply_process import start_bot_reply, stop_bot_reply
from dashboard.state import FRONTEND_DIST, FRONTEND_AVAILABLE
from dashboard.services.sessions_service import cleanup_login_flows
from dashboard.worker_lock import WorkerLock

WORKER_LOCK = WorkerLock(ROOT_DIR / "6_messaging" / "65" / "data" / "dashboard-workers.lock")


@asynccontextmanager
async def lifespan(app: FastAPI):
    owns_workers = WORKER_LOCK.acquire()
    app.state.owns_ghost_worker = owns_workers
    reply_handle = start_bot_reply() if owns_workers else None
    if not owns_workers:
        print("[dashboard] another dashboard process owns Telegram workers; skipping worker launch.")
    try:
        yield
    finally:
        await cleanup_login_flows()
        if owns_workers:
            stop_ghost_bot()
        if reply_handle is not None:
            await stop_bot_reply(reply_handle)
        if owns_workers:
            WORKER_LOCK.release()


app = FastAPI(title="Telegram Suite Dashboard", dependencies=[Depends(require_auth)], lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.middleware("http")
async def ensure_csrf_cookie(request, call_next):
    """Guarantees every browser tab has a CSRF token before it can submit
    anything — pages read it back via `document.cookie` (fetch header) or a
    hidden form field, see dashboard/csrf.py."""
    from fastapi.responses import PlainTextResponse
    client_host = request.client.host if request.client else None
    if not is_secure_request(client_host, request.url.scheme, DASHBOARD_PUBLIC_ORIGIN):
        return PlainTextResponse("Remote dashboard access requires HTTPS", status_code=403)
    response = await call_next(request)
    if CSRF_COOKIE_NAME not in request.cookies:
        response.set_cookie(
            CSRF_COOKIE_NAME, new_csrf_token(), samesite="strict", httponly=False,
            secure=bool(DASHBOARD_PUBLIC_ORIGIN),
        )
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

    if not remote_binding_has_https_origin(host, DASHBOARD_PUBLIC_ORIGIN):
        print("Refusing to start: non-loopback DASHBOARD_HOST requires ")
        print("DASHBOARD_PUBLIC_ORIGIN=https://your-dashboard.example behind a TLS reverse proxy.")
        sys.exit(1)

    if host not in ("127.0.0.1", "localhost", "::1") and not DASHBOARD_PASSWORD:
        print(f"Refusing to start: DASHBOARD_HOST={host} is non-local but no DASHBOARD_PASSWORD is set.")
        print("Set DASHBOARD_PASSWORD in .env, or bind to 127.0.0.1.")
        sys.exit(1)

    if DASHBOARD_PASSWORD:
        print(f"Starting Dashboard on http://{host}:{port} (HTTP Basic auth enabled)")
    else:
        print(f"Starting Dashboard on http://{host}:{port} (no auth, loopback-only)")
    uvicorn.run(app, host=host, port=port)
