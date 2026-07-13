"""Sessions tab: listing/verification + active-session switcher. Login endpoints added in Tasks 4-5."""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from dashboard.state import list_sessions, get_active_session, ACTIVE_SESSION_COOKIE
from dashboard.services.sessions_service import check_all_sessions

_template_dir = str(Path(__file__).resolve().parent.parent / "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_template_dir),
    autoescape=select_autoescape(['html', 'xml']),
    cache_size=0
)

router = APIRouter(prefix="/sessions")


def _render_template(template_name: str, context: dict) -> str:
    """Render a template with context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


@router.get("", response_class=HTMLResponse)
async def sessions_page(request: Request):
    results = await check_all_sessions()
    html = _render_template("sessions.html", {
        "request": request,
        "results": results,
        "active_session": get_active_session(request),
        "all_sessions": list_sessions(),
    })
    return html


@router.post("/active")
async def set_active_session(session_name: str = Form(...)):
    resp = RedirectResponse(url="/sessions", status_code=303)
    resp.set_cookie(ACTIVE_SESSION_COOKIE, session_name)
    return resp
