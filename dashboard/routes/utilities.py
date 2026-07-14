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


# --- Purge routes (destructive: see purge_service.purge_my_messages type-to-confirm guard) ---
from dashboard.services.purge_service import scan_my_activity, preview_my_messages, purge_my_messages


@router.get("/purge", response_class=HTMLResponse)
async def purge_page(request: Request):
    return _render_template("utilities_purge.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/purge/scan/ws")
async def purge_scan_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = get_active_session(websocket)
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        chats = await scan_my_activity(session_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": len(chats), "total": len(chats),
            "message": f"Found {len(chats)} chats with your messages.", "done": True, "chats": chats,
        })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


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
    await websocket.accept()
    session_name = get_active_session(websocket)
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        params = await websocket.receive_json()
        group_id = int(params["group_id"])
        target_name = params["target_name"]
        confirm_name = params["confirm_name"]

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        result = await purge_my_messages(session_name, group_id, target_name, confirm_name, progress_cb=progress_cb)
        await websocket.send_json({
            "current": result["deleted_count"], "total": result["deleted_count"],
            "message": f"Deleted {result['deleted_count']} messages.", "done": True,
        })
    except WebSocketDisconnect:
        pass
    except ValueError as e:
        await websocket.send_json({"error": str(e)})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
