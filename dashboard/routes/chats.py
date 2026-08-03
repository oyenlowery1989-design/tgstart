"""Chats tab, extracted from 3_chat_management/30_list_chats.py."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from dashboard.state import get_active_session, list_sessions, FRONTEND_AVAILABLE
from dashboard.services.chats_service import list_dialogs, save_dialogs_csv
from dashboard.templates_env import render_template as _render_template

router = APIRouter(prefix="/chats")


@router.get("/api/dialogs")
async def api_dialogs(request: Request):
    active = get_active_session(request)
    if not active:
        raise HTTPException(400, "no active session")
    rows = await list_dialogs(active)
    save_dialogs_csv(rows)
    return {"active_session": active, "rows": rows}


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
    html = _render_template("chats.html", {
        "request": request, "rows": rows, "error": error,
        "active_session": active, "all_sessions": list_sessions(),
        "frontend_available": FRONTEND_AVAILABLE,
    })
    return html
