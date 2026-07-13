"""Sessions tab: listing/verification + active-session switcher. Login endpoints added in Tasks 4-5."""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from fastapi.responses import JSONResponse

from dashboard.state import list_sessions, get_active_session, ACTIVE_SESSION_COOKIE
from dashboard.services.sessions_service import check_all_sessions, start_phone_login, submit_code, submit_2fa

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


# --- Phone login routes ---

@router.get("/login", response_class=HTMLResponse)
async def login_phone_page(request: Request):
    html = _render_template("login_phone.html", {
        "request": request,
        "active_session": get_active_session(request),
        "all_sessions": list_sessions(),
    })
    return html


@router.post("/login/phone")
async def login_phone_submit(phone: str = Form(...)):
    return JSONResponse(await start_phone_login(phone))


@router.post("/login/code")
async def login_code_submit(flow_id: str = Form(...), code: str = Form(...)):
    return JSONResponse(await submit_code(flow_id, code))


@router.post("/login/2fa")
async def login_2fa_submit(flow_id: str = Form(...), password: str = Form(...)):
    return JSONResponse(await submit_2fa(flow_id, password))
