"""Stats tab, extracted from 5_monitoring/50_group_stats.py."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from dashboard.state import get_active_session, list_sessions
from dashboard.services.stats_service import group_stats

_template_dir = str(Path(__file__).resolve().parent.parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)

router = APIRouter(prefix="/stats")


def _render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


@router.get("", response_class=HTMLResponse)
async def stats_page(request: Request):
    return _render_template("stats.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/ws")
async def stats_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = get_active_session(websocket)
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
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
