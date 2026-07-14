"""Scraping tab, extracted from 4_scraping/41_scrape_links_advanced.py."""
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from dashboard.state import get_active_session, list_sessions
from dashboard.services.scrape_service import scrape_links

_template_dir = str(Path(__file__).resolve().parent.parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)

router = APIRouter(prefix="/scrape")


def _render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


@router.get("", response_class=HTMLResponse)
async def scrape_page(request: Request):
    return _render_template("scrape.html", {
        "request": request, "active_session": get_active_session(request), "all_sessions": list_sessions(),
    })


@router.websocket("/ws")
async def scrape_ws(websocket: WebSocket):
    await websocket.accept()
    session_name = get_active_session(websocket)
    if not session_name:
        await websocket.send_json({"error": "No active session set."})
        await websocket.close()
        return
    try:
        params = await websocket.receive_json()
        group_id = int(params["group_id"])
        keyword = params.get("keyword") or None
        startswith = params.get("startswith") or None
        since_date = params.get("since_date") or None
        message_limit = int(params["message_limit"]) if params.get("message_limit") else None
        resume = bool(params.get("resume", False))

        async def progress_cb(current: int, total: int, message: str):
            await websocket.send_json({"current": current, "total": total, "message": message})

        result = await scrape_links(
            session_name, group_id, keyword=keyword, startswith=startswith, since_date=since_date,
            message_limit=message_limit, resume=resume, progress_cb=progress_cb,
        )
        await websocket.send_json({
            "current": result.scanned, "total": result.scanned,
            "message": f"Done. {len(result.links)} unique links -> {result.csv_path}", "done": True,
        })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()
