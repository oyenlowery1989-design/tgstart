"""HTTP Basic auth, ported unchanged from 6_messaging/65/dashboard.py.

Reads the Authorization header off `HTTPConnection` (the shared base class of
Request and WebSocket) rather than using FastAPI's `HTTPBasic` security
utility, which is typed to `Request` and breaks (500s) when resolved as an
app-level dependency for a `websocket` route.
"""
import base64
import binascii
import os
import secrets
from fastapi import HTTPException
from starlette.requests import HTTPConnection
from dotenv import load_dotenv

load_dotenv()

DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def require_auth(conn: HTTPConnection) -> None:
    if not DASHBOARD_PASSWORD:
        # Fail closed regardless of how the app was launched (python dashboard/app.py
        # vs a bare `uvicorn dashboard.app:app --host 0.0.0.0`): without a password,
        # only loopback clients may proceed.
        client_host = conn.client.host if conn.client else None
        if client_host not in LOOPBACK_HOSTS:
            raise HTTPException(status_code=403, detail="Dashboard requires DASHBOARD_PASSWORD for non-loopback access")
        return
    auth_header = conn.headers.get("authorization", "")
    username = password = ""
    if auth_header.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            username, _, password = decoded.partition(":")
        except (binascii.Error, UnicodeDecodeError):
            pass
    valid_user = secrets.compare_digest(username, DASHBOARD_USER)
    valid_pass = secrets.compare_digest(password, DASHBOARD_PASSWORD)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})
