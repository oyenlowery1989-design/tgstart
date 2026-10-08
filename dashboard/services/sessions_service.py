"""Session listing/verification, extracted from 2_verify/2_verify_login_advanced.py."""
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from telethon import TelegramClient, errors

from dashboard.state import list_sessions, session_path, SESSIONS_DIR
from dashboard.tg_client import API_ID, API_HASH, session_lock
from utils.tg_utils import code_delivery_label

ProgressCB = Callable[[int, int, str], Awaitable[None]]
LOGIN_FLOW_TTL_SECONDS = 600


async def check_session(session_name: str) -> Dict[str, str]:
    status = "UNKNOWN"
    details = ""
    masked_phone = ""
    async with session_lock(session_name):
        client = TelegramClient(session_path(session_name), API_ID, API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                status = "INVALID"
                details = "Revoked or expired"
            else:
                me = await client.get_me()
                status = "ACTIVE"
                user_display = f"@{me.username}" if me.username else f"{me.first_name} {me.last_name or ''}".strip()
                details = f"{user_display} (ID: {me.id})"
                phone = str(me.phone or "")
                masked_phone = f"+{phone[:2]}••••{phone[-2:]}" if len(phone) >= 4 else ""
        except Exception as e:
            status = "ERROR"
            details = str(e)
        finally:
            await client.disconnect()
    return {"name": session_name, "status": status, "details": details, "phone": masked_phone}


async def check_all_sessions(progress_cb: Optional[ProgressCB] = None) -> List[Dict[str, str]]:
    names = list_sessions()
    results: List[Dict[str, str]] = []
    for i, name in enumerate(names, 1):
        if progress_cb:
            await progress_cb(i - 1, len(names), f"Checking {name}...")
        results.append(await check_session(name))
        if progress_cb:
            await progress_cb(i, len(names), f"Checked {name}")
    return results


# --- Phone login flow ---


@dataclass
class LoginFlow:
    id: str
    client: TelegramClient
    phone: Optional[str] = None
    phone_code_hash: Optional[str] = None
    temp_session_name: str = ""
    created_at: float = 0


_FLOWS: Dict[str, LoginFlow] = {}


async def _discard_flow(flows: Dict[str, object], flow_id: str) -> None:
    flow = flows.pop(flow_id, None)
    if flow is None:
        return
    await flow.client.disconnect()
    _cleanup_temp_session(flow.temp_session_name)


async def cleanup_login_flows(now: Optional[float] = None) -> None:
    """Disconnect and remove incomplete phone/QR flows older than ten minutes."""
    now = time.monotonic() if now is None else now
    for flows in (_FLOWS, _QR_FLOWS):
        expired = [flow_id for flow_id, flow in flows.items()
                   if now - flow.created_at >= LOGIN_FLOW_TTL_SECONDS]
        for flow_id in expired:
            await _discard_flow(flows, flow_id)


def _temp_session_path() -> str:
    SESSIONS_DIR.mkdir(exist_ok=True)
    return str(SESSIONS_DIR / f"temp_login_{int(time.time())}_{uuid.uuid4().hex[:6]}")


def _cleanup_temp_session(temp_name: str) -> None:
    """Removes a temp .session file left behind by a failed login attempt."""
    session_file = Path(f"{temp_name}.session")
    if session_file.exists():
        session_file.unlink()


async def _finalize_session(client: TelegramClient, temp_session_name: str) -> str:
    me = await client.get_me()
    username = me.username or f"user_{me.id}"
    await client.disconnect()
    target = SESSIONS_DIR / f"{username}.session"
    counter = 2
    while target.exists():
        target = SESSIONS_DIR / f"{username}({counter}).session"
        counter += 1
    os.rename(f"{temp_session_name}.session", target)
    return target.stem


async def start_phone_login(phone: str) -> Dict[str, str]:
    await cleanup_login_flows()
    temp_name = _temp_session_path()
    client = TelegramClient(temp_name, API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
    except errors.FloodWaitError as e:
        await client.disconnect()
        _cleanup_temp_session(temp_name)
        return {"status": "error", "error": f"Too many attempts. Wait {e.seconds}s."}
    except Exception as e:
        await client.disconnect()
        _cleanup_temp_session(temp_name)
        return {"status": "error", "error": str(e)}
    flow_id = uuid.uuid4().hex
    _FLOWS[flow_id] = LoginFlow(id=flow_id, client=client, phone=phone, phone_code_hash=sent.phone_code_hash, temp_session_name=temp_name, created_at=time.monotonic())
    return {"status": "code_sent", "flow_id": flow_id, "delivery": code_delivery_label(sent)}


async def submit_code(flow_id: str, code: str) -> Dict[str, str]:
    await cleanup_login_flows()
    flow = _FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "Login flow expired or not found."}
    try:
        await flow.client.sign_in(flow.phone, code, phone_code_hash=flow.phone_code_hash)
    except errors.SessionPasswordNeededError:
        return {"status": "need_2fa", "flow_id": flow_id}
    except errors.PhoneCodeInvalidError:
        return {"status": "error", "error": "Invalid code."}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}


async def submit_2fa(flow_id: str, password: str) -> Dict[str, str]:
    await cleanup_login_flows()
    flow = _FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "Login flow expired or not found."}
    try:
        await flow.client.sign_in(password=password)
    except Exception as e:
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}


# --- QR login flow ---
import base64
import io

import qrcode


@dataclass
class QRFlow:
    id: str
    client: TelegramClient
    qr_obj: object
    temp_session_name: str
    created_at: float


_QR_FLOWS: Dict[str, QRFlow] = {}


async def start_qr_flow() -> Dict[str, str]:
    await cleanup_login_flows()
    temp_name = _temp_session_path()
    client = TelegramClient(temp_name, API_ID, API_HASH)
    try:
        await client.connect()
        qr_obj = await client.qr_login()
        img = qrcode.make(qr_obj.url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        await client.disconnect()
        _cleanup_temp_session(temp_name)
        raise
    flow_id = uuid.uuid4().hex
    _QR_FLOWS[flow_id] = QRFlow(id=flow_id, client=client, qr_obj=qr_obj, temp_session_name=temp_name, created_at=time.monotonic())
    return {"flow_id": flow_id, "qr_png_b64": png_b64}


async def wait_qr_flow(flow_id: str) -> Dict[str, str]:
    await cleanup_login_flows()
    flow = _QR_FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "QR flow expired or not found."}
    try:
        remaining = LOGIN_FLOW_TTL_SECONDS - (time.monotonic() - flow.created_at)
        await asyncio.wait_for(flow.qr_obj.wait(), timeout=max(remaining, 0))
    except asyncio.TimeoutError:
        await _discard_flow(_QR_FLOWS, flow_id)
        return {"status": "error", "error": "QR login expired. Start again."}
    except errors.SessionPasswordNeededError:
        return {"status": "need_2fa", "flow_id": flow_id}
    except Exception as e:
        if "PasswordNeeded" in str(e) or "password is required" in str(e):
            return {"status": "need_2fa", "flow_id": flow_id}
        del _QR_FLOWS[flow_id]
        await flow.client.disconnect()
        _cleanup_temp_session(flow.temp_session_name)
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _QR_FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}


async def submit_qr_2fa(flow_id: str, password: str) -> Dict[str, str]:
    await cleanup_login_flows()
    flow = _QR_FLOWS.get(flow_id)
    if not flow:
        return {"status": "error", "error": "QR flow expired or not found."}
    try:
        await flow.client.sign_in(password=password)
    except Exception as e:
        del _QR_FLOWS[flow_id]
        await flow.client.disconnect()
        _cleanup_temp_session(flow.temp_session_name)
        return {"status": "error", "error": str(e)}
    session_name = await _finalize_session(flow.client, flow.temp_session_name)
    del _QR_FLOWS[flow_id]
    return {"status": "done", "session_name": session_name}


async def delete_session(session_name: str) -> None:
    """Removes the local .session file only — does not revoke the login on
    Telegram's side. Acquires the same per-session lock used by scrape/scan
    operations so a delete can't race a live client using the file."""
    async with session_lock(session_name):
        base = Path(session_path(session_name))
        base.with_suffix(".session").unlink(missing_ok=True)
        base.with_suffix(".session-journal").unlink(missing_ok=True)


if __name__ == "__main__":
    import asyncio
    import inspect
    assert inspect.iscoroutinefunction(check_session)
    assert inspect.iscoroutinefunction(check_all_sessions)
    assert inspect.iscoroutinefunction(delete_session)
    result = asyncio.run(check_all_sessions())
    print("sessions_service.py smoke check OK:", result)
