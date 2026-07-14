"""Utilities tab: participation finder (this task) + purge (Task 11)."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from dashboard.state import get_active_session, list_sessions
from dashboard.services.participation_service import find_participation

_template_dir = str(Path(__file__).resolve().parent.parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)

router = APIRouter(prefix="/utilities")


def _render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


@router.get("/participation", response_class=HTMLResponse)
async def participation_page(request: Request):
    return _render_template("utilities_participation.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/participation/ws")
async def participation_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = get_active_session(websocket)
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
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
