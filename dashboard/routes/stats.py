"""Stats tab, extracted from 5_monitoring/50_group_stats.py."""
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse

from dashboard.state import get_active_session, list_sessions, FRONTEND_AVAILABLE
from dashboard.services.stats_service import group_stats
from dashboard.templates_env import render_template as _render_template
from dashboard.ws_utils import ws_session

router = APIRouter(prefix="/stats")


@router.get("", response_class=HTMLResponse)
async def stats_page(request: Request):
    return _render_template("stats.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
        "frontend_available": FRONTEND_AVAILABLE,
    })


@router.websocket("/ws")
async def stats_ws(websocket: WebSocket):
    async with ws_session(websocket) as session_name:
        if not session_name:
            return
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


api_router = APIRouter(prefix="/api/stats")


@api_router.get("/session")
async def api_stats_session(request: Request):
    return {"active_session": get_active_session(request), "all_sessions": list_sessions()}


@api_router.websocket("/ws")
async def api_stats_ws(websocket: WebSocket):
    async with ws_session(websocket) as session_name:
        if not session_name:
            return
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
            "total_scanned": result.total_scanned, "unique_senders": result.unique_senders,
            "busiest_hour": result.busiest_hour,
        })
