"""Utilities tab: participation finder (this task) + purge (Task 11)."""
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import HTMLResponse

from dashboard.state import get_active_session, list_sessions
from dashboard.services.participation_service import find_participation
from dashboard.templates_env import render_template as _render_template
from dashboard.ws_utils import ws_session

router = APIRouter(prefix="/utilities")


@router.get("/participation", response_class=HTMLResponse)
async def participation_page(request: Request):
    return _render_template("utilities_participation.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/participation/ws")
async def participation_ws(websocket: WebSocket):
    async with ws_session(websocket) as session_name:
        if not session_name:
            return

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        results = await find_participation(session_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": len(results), "total": len(results),
            "message": f"Found {len(results)} chats with your messages.", "done": True, "results": results,
        })


# --- Purge routes (destructive: see purge_service.purge_my_messages type-to-confirm guard,
#     which checks confirm_name against a server-resolved chat name, not client input) ---
from dashboard.services.purge_service import scan_my_activity, preview_my_messages, purge_my_messages


@router.get("/purge", response_class=HTMLResponse)
async def purge_page(request: Request):
    return _render_template("utilities_purge.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/purge/scan/ws")
async def purge_scan_ws(websocket: WebSocket):
    async with ws_session(websocket) as session_name:
        if not session_name:
            return

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        chats = await scan_my_activity(session_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": len(chats), "total": len(chats),
            "message": f"Found {len(chats)} chats with your messages.", "done": True, "chats": chats,
        })


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
    async with ws_session(websocket) as session_name:
        if not session_name:
            return
        params = await websocket.receive_json()
        group_id = int(params["group_id"])
        # NOTE: params.get("target_name") is client-supplied and used for display only
        # (e.g. echoing back what the UI showed) - it must never be used for the
        # type-to-confirm safety check. purge_my_messages resolves the real chat name
        # itself via client.get_entity(group_id) and checks confirm_name against that.
        confirm_name = params["confirm_name"]

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        result = await purge_my_messages(session_name, group_id, confirm_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": result["deleted_count"], "total": result["deleted_count"],
            "message": f"Deleted {result['deleted_count']} messages.", "done": True,
        })
