"""Group Users tab, extracted from 3_chat_management/31_list_group_users.py."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from dashboard.state import get_active_session, list_sessions
from dashboard.services.group_users_service import (
    list_group_users, save_group_users_csv, EXPORT_PHONE_NUMBERS_DEFAULT, AGGRESSIVE_SCRAPE_DEFAULT,
)

_template_dir = str(Path(__file__).resolve().parent.parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)

router = APIRouter(prefix="/groups")


def _render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


@router.get("/{group_id}/users", response_class=HTMLResponse)
async def group_users_page(request: Request, group_id: int):
    html = _render_template("groups.html", {
        "request": request, "group_id": group_id,
        "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })
    return html


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
