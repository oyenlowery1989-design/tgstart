"""Chats tab, extracted from 3_chat_management/30_list_chats.py."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from dashboard.state import get_active_session, list_sessions
from dashboard.services.chats_service import list_dialogs, save_dialogs_csv

_template_dir = str(Path(__file__).resolve().parent.parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)

router = APIRouter(prefix="/chats")


def _render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


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
    })
    return html
