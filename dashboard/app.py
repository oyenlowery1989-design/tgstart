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
