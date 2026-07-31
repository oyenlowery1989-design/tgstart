"""Sessions tab: listing/verification + active-session switcher. Login endpoints added in Tasks 4-5."""
from fastapi import APIRouter, Request, Form, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from dashboard.state import list_sessions, get_active_session, ACTIVE_SESSION_COOKIE, FRONTEND_AVAILABLE
from dashboard.services.sessions_service import (
    check_all_sessions,
    start_phone_login,
    submit_code,
    submit_2fa,
    start_qr_flow,
    wait_qr_flow,
    submit_qr_2fa,
)
from dashboard.templates_env import render_template as _render_template
from dashboard.ws_utils import ws_session

router = APIRouter(prefix="/sessions")


@router.get("", response_class=HTMLResponse)
async def sessions_page(request: Request):
    results = await check_all_sessions()
    html = _render_template("sessions.html", {
        "request": request,
        "results": results,
        "active_session": get_active_session(request),
        "all_sessions": list_sessions(),
        "frontend_available": FRONTEND_AVAILABLE,
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
        "frontend_available": FRONTEND_AVAILABLE,
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


# --- QR login routes ---

@router.get("/login/qr", response_class=HTMLResponse)
async def login_qr_page(request: Request):
    html = _render_template("login_qr.html", {
        "request": request,
        "active_session": get_active_session(request),
        "all_sessions": list_sessions(),
        "frontend_available": FRONTEND_AVAILABLE,
    })
    return html


@router.websocket("/login/qr/ws")
async def login_qr_ws(websocket: WebSocket):
    async with ws_session(websocket, require_session=False):
        started = await start_qr_flow()
        await websocket.send_json({"state": "waiting", "qr_png_b64": started["qr_png_b64"]})
        result = await wait_qr_flow(started["flow_id"])
        if result["status"] == "need_2fa":
            await websocket.send_json({"state": "need_2fa", "flow_id": result["flow_id"]})
            msg = await websocket.receive_json()
            result = await submit_qr_2fa(result["flow_id"], msg["password"])
        if result["status"] == "done":
            await websocket.send_json({"state": "done", "session_name": result["session_name"]})
        else:
            await websocket.send_json({"state": "error", "error": result.get("error", "Unknown error")})
