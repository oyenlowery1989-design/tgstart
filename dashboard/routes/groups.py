"""Group Users tab, extracted from 3_chat_management/31_list_group_users.py."""
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse

from dashboard.state import get_active_session, list_sessions
from dashboard.services.group_users_service import (
    list_group_users, save_group_users_csv, EXPORT_PHONE_NUMBERS_DEFAULT, AGGRESSIVE_SCRAPE_DEFAULT,
)
from dashboard.templates_env import render_template as _render_template
from dashboard.ws_utils import ws_session

router = APIRouter(prefix="/groups")


@router.get("/{group_id}/users", response_class=HTMLResponse)
async def group_users_page(request: Request, group_id: int):
    html = _render_template("groups.html", {
        "request": request, "group_id": group_id,
        "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })
    return html


@router.websocket("/{group_id}/users/ws")
async def group_users_ws(websocket: WebSocket, group_id: int):
    async with ws_session(websocket) as session_name:
        if not session_name:
            return

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        users = await list_group_users(
            session_name, group_id,
            export_phone_numbers=EXPORT_PHONE_NUMBERS_DEFAULT,
            aggressive=AGGRESSIVE_SCRAPE_DEFAULT,
            progress_cb=progress_cb,
        )
        csv_path = save_group_users_csv(str(group_id), group_id, users, EXPORT_PHONE_NUMBERS_DEFAULT)
        await websocket.send_json({"current": len(users), "total": len(users), "message": f"Saved {csv_path}", "done": True})
